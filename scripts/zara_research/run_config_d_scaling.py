"""Phase 1C Config D (4 Concurrent Workers) Production Scaling Engine.

Executes large-scale enrichment across all remaining QUEUED products:
- Config D: 4 concurrent Edge browser workers with route aborting & attached JSON-LD readiness
- Decoupled Layer 3 offline local parsing
- Staged persistence with O(1) in-memory indexes and atomic master table flush
- 500-product chunks with strict invariant verification after each chunk
- Controlled retry sweep for any transient FAILED_RETRYABLE items
- Generates chunk reports and final Phase 1C completion report
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/zara_research'))

from page_source_collector import (
    collect_page_sources_concurrent,
    clean_filename_id,
    save_page_source_bundle,
    EDGE_PATH
)
from local_product_parser import parse_page_source_from_disk
from enrich_product_details import build_normalized_records, PARSER_VERSION
from staged_batch_writer import StagedBatchManager, atomic_write_json

STATE = ROOT / 'data/zara'
REPORTS = ROOT / 'reports'
RAW_DETAILS = ROOT / 'data/raw/zara/product_details'
RAW_SOURCES = ROOT / 'data/raw/zara/page_sources'


class InvariantViolationError(Exception):
    """Raised when catalogue integrity check fails."""
    pass


def validate_invariants(expected_queue_len: int = 6276) -> Dict[str, Any]:
    """Strictly validate all relational and queue invariants."""
    q_path = STATE / 'product_detail_queue.json'
    p_path = STATE / 'product_details.json'
    v_path = STATE / 'product_variants.json'
    c_path = STATE / 'product_colors.json'
    i_path = STATE / 'product_images.json'
    u_path = STATE / 'unique_products.json'

    queue = json.loads(q_path.read_text(encoding='utf-8'))
    prods = json.loads(p_path.read_text(encoding='utf-8'))
    variants = json.loads(v_path.read_text(encoding='utf-8'))
    colors = json.loads(c_path.read_text(encoding='utf-8'))
    images = json.loads(i_path.read_text(encoding='utf-8'))
    unique_prods = json.loads(u_path.read_text(encoding='utf-8'))

    # 1. Total queue count invariant
    if len(queue) != expected_queue_len:
        raise InvariantViolationError(f"Queue count mismatch: {len(queue)} != {expected_queue_len}")

    # 2. No duplicate product IDs
    prod_ids = [p["product_id"] for p in prods]
    if len(prod_ids) != len(set(prod_ids)):
        dups = [pid for pid, cnt in Counter(prod_ids).items() if cnt > 1]
        raise InvariantViolationError(f"Duplicate product IDs in product_details.json: {dups[:5]}")

    prod_id_set = set(prod_ids)
    unique_id_set = {u["product_id"] for u in unique_prods}

    # 3. Every COMPLETE queue item has a normalized product record
    complete_queue_ids = {q["id"] for q in queue if q.get("status") == "COMPLETE"}
    missing_prods = complete_queue_ids - prod_id_set
    if missing_prods:
        raise InvariantViolationError(f"COMPLETE queue items missing from product_details.json: {list(missing_prods)[:5]}")

    # 4. Normalized products must exist in unique_products registry
    missing_cat = prod_id_set - unique_id_set
    if missing_cat:
        raise InvariantViolationError(f"Normalized products not in unique_products.json: {list(missing_cat)[:5]}")

    # 5. Zero orphan variants
    orphan_vars = [v for v in variants if v["product_id"] not in prod_id_set]
    if orphan_vars:
        raise InvariantViolationError(f"Found {len(orphan_vars)} orphan variants")

    # 6. Zero orphan colors
    orphan_cols = [c for c in colors if c["product_id"] not in prod_id_set]
    if orphan_cols:
        raise InvariantViolationError(f"Found {len(orphan_cols)} orphan colors")

    # 7. Zero orphan images
    orphan_imgs = [img for img in images if img["product_id"] not in prod_id_set]
    if orphan_imgs:
        raise InvariantViolationError(f"Found {len(orphan_imgs)} orphan images")

    # 8. Raw evidence existence for all COMPLETE products
    raw_files = set(os.listdir(RAW_DETAILS)) if RAW_DETAILS.exists() else set()
    missing_raw = []
    for p in prods:
        clean_pid = p["product_id"].replace(":", "_").replace("/", "_")
        src_id = p.get("source_product_id") or p["product_id"].split(":")[-1]
        if f"{clean_pid}.json" not in raw_files and f"{src_id}.json" not in raw_files:
            missing_raw.append(p["product_id"])
    if missing_raw:
        raise InvariantViolationError(f"COMPLETE products missing raw evidence: {missing_raw[:5]}")

    # 9. Price coverage health check
    valid_prices = sum(1 for p in prods if p.get("current_price"))
    price_cov = (valid_prices / len(prods)) * 100.0 if prods else 0.0

    return {
        "queue_total": len(queue),
        "status_distribution": dict(Counter(q.get("status") for q in queue)),
        "normalized_products": len(prods),
        "normalized_variants": len(variants),
        "normalized_colors": len(colors),
        "normalized_images": len(images),
        "price_coverage_percent": round(price_cov, 2)
    }


def record_chunk_report(chunk_num: int, chunk_metrics: Dict[str, Any], validation_info: Dict[str, Any]) -> None:
    """Append chunk report to reports/phase_1c_chunk_reports.json."""
    REPORTS.mkdir(parents=True, exist_ok=True)
    report_file = REPORTS / 'phase_1c_chunk_reports.json'

    chunk_reports = []
    if report_file.exists():
        try:
            chunk_reports = json.loads(report_file.read_text(encoding='utf-8'))
        except Exception:
            chunk_reports = []

    report_entry = {
        "chunk_number": chunk_num,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": chunk_metrics,
        "validation": validation_info
    }
    chunk_reports.append(report_entry)

    atomic_write_json(report_file, chunk_reports)


def run_chunk(
    chunk_num: int,
    chunk_items: List[Dict[str, Any]],
    manager: StagedBatchManager,
    concurrency_level: int = 4
) -> Dict[str, Any]:
    """Execute a single chunk through Layer 2 Concurrent Fetch and Layer 3 Offline Local Parse."""
    t0_chunk = time.perf_counter()
    print(f"\n=================================================================")
    print(f"STARTING CHUNK #{chunk_num}: {len(chunk_items)} products (Config D: {concurrency_level} workers)")
    print(f"=================================================================")

    up_by_id = {
        p['product_id']: p
        for p in json.loads((STATE / 'unique_products.json').read_text(encoding='utf-8'))
    }

    # 1. LAYER 2: Concurrent Public-Page Source Collection
    t0_fetch = time.perf_counter()
    fetch_summary = collect_page_sources_concurrent(
        product_items=chunk_items,
        concurrency_level=concurrency_level,
        output_dir=RAW_SOURCES,
        timeout_ms=45000,
        headless=False,
        edge_path=EDGE_PATH
    )
    t_fetch = time.perf_counter() - t0_fetch
    print(f"[Chunk #{chunk_num}] L2 Fetch completed in {t_fetch:.1f}s ({len(chunk_items)/t_fetch:.2f} pages/s)")

    # 2. LAYER 3: Offline BeautifulSoup + JSON Local Parsing & Normalization
    t0_pipeline = time.perf_counter()
    completed_in_chunk = 0
    terminal_in_chunk = 0
    retryable_in_chunk = 0

    now_iso = datetime.now(timezone.utc).isoformat()
    fetch_results_by_id = {r['product_id']: r for r in fetch_summary.get('results', [])}

    for idx, item in enumerate(chunk_items, 1):
        pid = item['id']
        url = item.get('url')
        clean_id = clean_filename_id(pid)
        html_file = RAW_SOURCES / f"{clean_id}.html"
        meta_file = RAW_SOURCES / f"{clean_id}.meta.json"

        f_meta = fetch_results_by_id.get(pid, {})
        has_source = html_file.exists() and f_meta.get("content_length", 0) > 0

        if not has_source:
            # Classification of failure
            err = f_meta.get("error", "Source HTML not captured")
            if f_meta.get("http_status") == 404 or "404" in str(err):
                item["status"] = "FAILED_TERMINAL"
                item["error"] = "HTTP 404 Not Found"
                terminal_in_chunk += 1
            else:
                item["status"] = "FAILED_RETRYABLE"
                item["error"] = err
                retryable_in_chunk += 1
            item["attempt_count"] = item.get("attempt_count", 0) + 1
            item["last_attempt_at"] = now_iso
            manager.queue_by_id[pid] = item
            continue

        try:
            evidence = parse_page_source_from_disk(html_file, meta_file)
            if evidence.get("http_status") == 404:
                item["status"] = "FAILED_TERMINAL"
                item["error"] = "HTTP 404 Not Found"
                item["attempt_count"] = item.get("attempt_count", 0) + 1
                item["last_attempt_at"] = now_iso
                manager.queue_by_id[pid] = item
                terminal_in_chunk += 1
                continue

            global_p = up_by_id.get(pid, {"product_id": pid, "product_url": url})
            prod_rec, vars_rec, cols_rec, imgs_rec, img_stats, price_stats = build_normalized_records(
                evidence, global_p, now_iso
            )

            # Raw audit evidence JSON structure
            raw_audit = {
                "product_id": pid,
                "source_url": url,
                "final_url": evidence.get("final_url"),
                "canonical_url": evidence.get("canonical_url"),
                "enriched_at": now_iso,
                "http_status": evidence.get("http_status"),
                "page_title": evidence.get("page_title"),
                "headings": evidence.get("headings"),
                "jsonld_raw": evidence.get("jsonld_raw"),
                "parsed_product_groups": evidence.get("parsed_product_groups"),
                "dom_colors": evidence.get("dom_colors"),
                "rendered_price": evidence.get("rendered_price"),
                "rendered_description": evidence.get("rendered_description"),
                "comp_care_text": evidence.get("comp_care_text"),
                "raw_images_count": len(evidence.get("raw_images", [])),
                "valid_images_count": len(imgs_rec),
                "variants_count": len(vars_rec),
                "colors_count": len(cols_rec),
                "pricing_stats": price_stats,
                "source_content_hash": prod_rec["source_content_hash"],
                "parser_version": PARSER_VERSION
            }

            item["status"] = "COMPLETE"
            item["attempt_count"] = item.get("attempt_count", 0) + 1
            item["last_attempt_at"] = now_iso
            item["error"] = None
            item["checkpoint"] = {
                "enriched_at": now_iso,
                "content_hash": prod_rec["source_content_hash"],
                "variants_count": len(vars_rec),
                "colors_count": len(cols_rec),
                "images_count": len(imgs_rec),
                "price": prod_rec["current_price"]
            }

            # Price record for history
            price_rec = None
            if prod_rec.get("current_price"):
                price_rec = {
                    "history_id": f"{pid}:{now_iso}",
                    "product_id": pid,
                    "observed_at": now_iso,
                    "current_price": prod_rec["current_price"],
                    "original_price": prod_rec.get("original_price"),
                    "sale_price": prod_rec.get("sale_price"),
                    "is_on_sale": prod_rec.get("is_on_sale", False),
                    "price_currency": "USD"
                }

            manager.stage_product_enrichment(
                product_id=pid,
                prod_rec=prod_rec,
                vars_rec=vars_rec,
                cols_rec=cols_rec,
                imgs_rec=imgs_rec,
                price_rec=price_rec,
                raw_evidence=raw_audit,
                queue_item=item
            )
            completed_in_chunk += 1

        except Exception as e:
            item["status"] = "FAILED_RETRYABLE"
            item["attempt_count"] = item.get("attempt_count", 0) + 1
            item["last_attempt_at"] = now_iso
            item["error"] = str(e)
            manager.queue_by_id[pid] = item
            retryable_in_chunk += 1
            print(f"[Chunk #{chunk_num}] Parser error on {pid}: {e}")

    # Final flush for chunk boundary
    manager.flush()
    t_pipeline = time.perf_counter() - t0_pipeline
    total_chunk_sec = time.perf_counter() - t0_chunk

    # Post-chunk invariant validation
    validation_info = validate_invariants(expected_queue_len=6276)

    metrics = {
        "chunk_number": chunk_num,
        "attempted": len(chunk_items),
        "completed": completed_in_chunk,
        "failed_terminal": terminal_in_chunk,
        "failed_retryable": retryable_in_chunk,
        "total_wall_sec": round(total_chunk_sec, 2),
        "fetch_wall_sec": round(t_fetch, 2),
        "pipeline_wall_sec": round(t_pipeline, 2),
        "fetch_throughput_pages_per_sec": round(len(chunk_items) / t_fetch, 2) if t_fetch > 0 else 0.0,
        "e2e_throughput_pages_per_sec": round(len(chunk_items) / total_chunk_sec, 2) if total_chunk_sec > 0 else 0.0,
        "cumulative_complete": validation_info["status_distribution"].get("COMPLETE", 0),
        "remaining_queued": validation_info["status_distribution"].get("QUEUED", 0),
        "cumulative_failed_terminal": validation_info["status_distribution"].get("FAILED_TERMINAL", 0),
        "cumulative_failed_retryable": validation_info["status_distribution"].get("FAILED_RETRYABLE", 0),
        "price_coverage_percent": validation_info["price_coverage_percent"]
    }

    record_chunk_report(chunk_num, metrics, validation_info)

    print(f"\n--- Chunk #{chunk_num} Summary ---")
    print(f"Attempted: {metrics['attempted']} | Completed: {metrics['completed']} | Fail (Term/Retry): {terminal_in_chunk}/{retryable_in_chunk}")
    print(f"Duration: {metrics['total_wall_sec']}s (Fetch: {metrics['fetch_wall_sec']}s, Pipeline: {metrics['pipeline_wall_sec']}s)")
    print(f"Throughput: {metrics['e2e_throughput_pages_per_sec']} E2E products/sec ({metrics['fetch_throughput_pages_per_sec']} fetch pages/sec)")
    print(f"Catalogue Status: COMPLETE={metrics['cumulative_complete']} | QUEUED={metrics['remaining_queued']} | FAILED_TERM={metrics['cumulative_failed_terminal']} | FAILED_RETRY={metrics['cumulative_failed_retryable']}")
    print(f"Invariants: VALIDATED OK (Total: {validation_info['queue_total']}, Prods: {validation_info['normalized_products']}, Vars: {validation_info['normalized_variants']}, Imgs: {validation_info['normalized_images']}, Price Cov: {metrics['price_coverage_percent']}%)")

    return metrics


def git_commit_checkpoint(message: str) -> Optional[str]:
    """Execute clean git commit for chunk checkpoint."""
    try:
        subprocess.run(["git", "add", "data/zara/", "data/raw/zara/product_details/", "reports/"], cwd=ROOT, check=True)
        res = subprocess.run(["git", "commit", "-m", message], cwd=ROOT, capture_output=True, text=True)
        if res.returncode == 0:
            commit_hash = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
            print(f"Git checkpoint committed: {commit_hash} - '{message}'")
            return commit_hash
    except Exception as e:
        print(f"Warning: Git commit skipped or failed: {e}")
    return None


def run_first_500_chunk():
    """Run strictly the first 500-product chunk and report."""
    queue = json.loads((STATE / 'product_detail_queue.json').read_text(encoding='utf-8'))
    queued_items = [q for q in queue if q.get('status') == 'QUEUED']
    print(f"Total QUEUED items available: {len(queued_items)}")

    if not queued_items:
        print("No QUEUED products found.")
        return

    chunk_1_items = queued_items[:500]
    manager = StagedBatchManager(state_dir=STATE, raw_dir=ROOT / 'data/raw/zara', flush_interval=50)

    metrics = run_chunk(chunk_num=1, chunk_items=chunk_1_items, manager=manager, concurrency_level=4)
    git_commit_checkpoint(f"feat(phase-1c): complete chunk 1 (500 products) with Config D (cumulative COMPLETE={metrics['cumulative_complete']})")


def run_all_remaining():
    """Run all remaining chunks until QUEUED reaches 0, followed by retry sweep."""
    chunk_num = 1
    # Determine next chunk number from existing chunk reports
    report_file = REPORTS / 'phase_1c_chunk_reports.json'
    existing_reports = json.loads(report_file.read_text(encoding='utf-8')) if report_file.exists() else []
    int_chunks = [r.get("chunk_number") for r in existing_reports if isinstance(r.get("chunk_number"), int)]
    chunk_num = max(int_chunks, default=0) + 1
    print(f"Resuming scaling runner at chunk #{chunk_num}...")
    manager = StagedBatchManager(state_dir=STATE, raw_dir=ROOT / 'data/raw/zara', flush_interval=50)

    while True:
        queue = json.loads((STATE / 'product_detail_queue.json').read_text(encoding='utf-8'))
        queued_items = [q for q in queue if q.get('status') == 'QUEUED']
        if not queued_items:
            print("\nAll QUEUED products have been attempted!")
            break

        chunk_items = queued_items[:500]
        metrics = run_chunk(chunk_num=chunk_num, chunk_items=chunk_items, manager=manager, concurrency_level=4)
        git_commit_checkpoint(f"feat(phase-1c): complete chunk {chunk_num} (cumulative COMPLETE={metrics['cumulative_complete']})")
        chunk_num += 1

    # Retry sweep for FAILED_RETRYABLE
    queue = json.loads((STATE / 'product_detail_queue.json').read_text(encoding='utf-8'))
    retryable_items = [q for q in queue if q.get('status') == 'FAILED_RETRYABLE']
    if retryable_items:
        print(f"\n=================================================================")
        print(f"STARTING CONTROLLED RETRY SWEEP: {len(retryable_items)} products")
        print(f"=================================================================")
        retry_metrics = run_chunk(chunk_num=999, chunk_items=retryable_items, manager=manager, concurrency_level=4)
        git_commit_checkpoint(f"feat(phase-1c): complete retry sweep (cumulative COMPLETE={retry_metrics['cumulative_complete']})")

    # Generate final Phase 1C report
    generate_final_report()


def generate_final_report():
    """Generate final comprehensive Phase 1C report."""
    val = validate_invariants(6276)
    queue = json.loads((STATE / 'product_detail_queue.json').read_text(encoding='utf-8'))
    prods = json.loads((STATE / 'product_details.json').read_text(encoding='utf-8'))
    vars_ = json.loads((STATE / 'product_variants.json').read_text(encoding='utf-8'))
    cols = json.loads((STATE / 'product_colors.json').read_text(encoding='utf-8'))
    imgs = json.loads((STATE / 'product_images.json').read_text(encoding='utf-8'))

    status_counts = Counter(q.get("status") for q in queue)
    report_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_catalogue_queue": len(queue),
        "status_distribution": dict(status_counts),
        "normalized_products": len(prods),
        "normalized_variants": len(vars_),
        "normalized_colors": len(cols),
        "normalized_images": len(imgs),
        "price_coverage_percent": val["price_coverage_percent"],
        "phase_status": "PHASE_1C_COMPLETE" if status_counts.get("QUEUED", 0) == 0 else "IN_PROGRESS"
    }

    report_path = REPORTS / 'phase_1c_final_completion_report.json'
    atomic_write_json(report_path, report_data)

    md_lines = [
        "# Phase 1C Final Completion Report",
        "",
        f"**Date**: {report_data['timestamp']}",
        f"**Final Status**: **{report_data['phase_status']}**",
        "",
        "### Catalogue Summary",
        f"- Total Queue: **{report_data['total_catalogue_queue']:,}**",
        f"- COMPLETE: **{status_counts.get('COMPLETE', 0):,}**",
        f"- FAILED_TERMINAL: **{status_counts.get('FAILED_TERMINAL', 0):,}**",
        f"- FAILED_RETRYABLE: **{status_counts.get('FAILED_RETRYABLE', 0):,}**",
        f"- QUEUED: **{status_counts.get('QUEUED', 0):,}**",
        "",
        "### Normalized Entities",
        f"- Products: **{report_data['normalized_products']:,}**",
        f"- Variants: **{report_data['normalized_variants']:,}**",
        f"- Colors: **{report_data['normalized_colors']:,}**",
        f"- Images: **{report_data['normalized_images']:,}**",
        f"- Price Coverage: **{report_data['price_coverage_percent']}%**"
    ]
    (REPORTS / 'phase_1c_final_completion_report.md').write_text("\n".join(md_lines), encoding='utf-8')
    print(f"\nFinal Phase 1C report saved to {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-chunk-only", action="store_true", help="Run only chunk 1 (500 products)")
    parser.add_argument("--all", action="store_true", help="Run all remaining QUEUED products")
    args = parser.parse_args()

    if args.first_chunk_only:
        run_first_500_chunk()
    elif args.all:
        run_all_remaining()
    else:
        run_first_500_chunk()
