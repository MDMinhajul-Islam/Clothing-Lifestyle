"""Phase 1C Large-Scale Product Detail Enrichment Scaling Runner.

Executes:
1. 500-product chunks across all remaining QUEUED products.
2. Automated invariant validation after each chunk.
3. Compact chunk progress reporting.
4. Legacy PARTIAL migration pass (49 items).
5. Controlled failure retry sweep across FAILED_RETRYABLE.
6. Comprehensive Phase 1C completion audit and report.
"""

import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/zara_research'))

from enrich_product_details import run_enrichment_batch
from card_id_resolver import execute_card_id_resolution

STATE = ROOT / 'data/zara'
REPORTS = ROOT / 'reports'
RAW_DETAILS = ROOT / 'data/raw/zara/product_details'


class InvariantViolationError(Exception):
    """Raised when a data integrity validation fails."""
    pass


def validate_invariants(expected_queue_len=6276):
    """Validate all catalogue invariants across normalized and queue datasets."""
    with open(STATE / 'product_detail_queue.json', 'r', encoding='utf-8') as f:
        queue = json.load(f)
    with open(STATE / 'product_details.json', 'r', encoding='utf-8') as f:
        prods = json.load(f)
    with open(STATE / 'product_variants.json', 'r', encoding='utf-8') as f:
        variants = json.load(f)
    with open(STATE / 'product_colors.json', 'r', encoding='utf-8') as f:
        colors = json.load(f)
    with open(STATE / 'product_images.json', 'r', encoding='utf-8') as f:
        images = json.load(f)
    with open(STATE / 'unique_products.json', 'r', encoding='utf-8') as f:
        unique_prods = json.load(f)

    # 1. Queue count invariant
    if len(queue) != expected_queue_len:
        raise InvariantViolationError(f"Queue count mismatch: {len(queue)} != {expected_queue_len}")

    # 2. No duplicate product IDs
    prod_ids = [p["product_id"] for p in prods]
    if len(prod_ids) != len(set(prod_ids)):
        duplicates = [pid for pid, count in Counter(prod_ids).items() if count > 1]
        raise InvariantViolationError(f"Duplicate product IDs in product_details.json: {duplicates[:5]}")

    prod_id_set = set(prod_ids)
    unique_id_set = {u["product_id"] for u in unique_prods}

    # 3. Every COMPLETE queue item has a normalized product record
    complete_queue_ids = {q["id"] for q in queue if q.get("status") == "COMPLETE"}
    missing_prods = complete_queue_ids - prod_id_set
    if missing_prods:
        raise InvariantViolationError(f"COMPLETE queue items missing from product_details.json: {list(missing_prods)[:5]}")

    # 4. Normalized products reference unique_products catalogue
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

    # 8. Raw evidence existence for all complete products
    raw_files = set(os.listdir(RAW_DETAILS)) if RAW_DETAILS.exists() else set()
    missing_raw = []
    for p in prods:
        src_id = p.get("source_product_id") or p["product_id"].split(":")[-1]
        if f"{src_id}.json" not in raw_files:
            missing_raw.append(p["product_id"])
    if missing_raw:
        raise InvariantViolationError(f"Normalized products missing raw evidence: {missing_raw[:5]}")

    return {
        "queue_total": len(queue),
        "normalized_products": len(prods),
        "normalized_variants": len(variants),
        "normalized_colors": len(colors),
        "normalized_images": len(images)
    }


def record_chunk_report(chunk_num, chunk_metrics, validation_info):
    """Persist chunk report to reports/phase_1c_chunk_reports.json."""
    REPORTS.mkdir(parents=True, exist_ok=True)
    report_file = REPORTS / 'phase_1c_chunk_reports.json'

    chunk_reports = []
    if report_file.exists():
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                chunk_reports = json.load(f)
        except Exception:
            chunk_reports = []

    report_entry = {
        "chunk_number": chunk_num,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": chunk_metrics,
        "cumulative_validation": validation_info
    }
    chunk_reports.append(report_entry)

    tmp_path = report_file.with_suffix('.tmp')
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(chunk_reports, f, indent=2, ensure_ascii=False)
    tmp_path.replace(report_file)


def generate_phase1c_final_report():
    """Generate and persist the comprehensive Phase 1C final report."""
    with open(STATE / 'product_detail_queue.json', 'r', encoding='utf-8') as f:
        queue = json.load(f)
    with open(STATE / 'product_details.json', 'r', encoding='utf-8') as f:
        prods = json.load(f)
    with open(STATE / 'product_variants.json', 'r', encoding='utf-8') as f:
        variants = json.load(f)
    with open(STATE / 'product_colors.json', 'r', encoding='utf-8') as f:
        colors = json.load(f)
    with open(STATE / 'product_images.json', 'r', encoding='utf-8') as f:
        images = json.load(f)
    with open(STATE / 'product_price_history.json', 'r', encoding='utf-8') as f:
        price_hist = json.load(f)

    q_counts = Counter(q.get("status") for q in queue)
    total_q = len(queue)
    complete_count = q_counts.get("COMPLETE", 0)
    partial_count = q_counts.get("PARTIAL", 0)
    retryable_count = q_counts.get("FAILED_RETRYABLE", 0)
    terminal_count = q_counts.get("FAILED_TERMINAL", 0)
    queued_count = q_counts.get("QUEUED", 0)

    # Pricing metrics
    with_price = [p for p in prods if p.get("current_price")]
    sale_prods = [p for p in prods if p.get("is_on_sale")]
    missing_price = [p for p in prods if not p.get("current_price")]
    currencies = Counter(p.get("currency") for p in prods)
    raw_files = set(os.listdir(RAW_DETAILS)) if RAW_DETAILS.exists() else set()
    
    price_conflicts = 0
    for rf in raw_files:
        try:
            with open(RAW_DETAILS / rf, 'r', encoding='utf-8') as f:
                rdoc = json.load(f)
                if rdoc.get("pricing_stats", {}).get("price_conflict"):
                    price_conflicts += 1
        except Exception:
            pass

    # Variant metrics
    prods_with_vars = len({v["product_id"] for v in variants})
    avail_dist = Counter(v.get("public_availability_state") for v in variants)
    vars_per_prod = [sum(1 for v in variants if v["product_id"] == p["product_id"]) for p in prods] or [0]

    # Color metrics
    prods_with_cols = len({c["product_id"] for c in colors})
    cols_per_prod = [sum(1 for c in colors if c["product_id"] == p["product_id"]) for p in prods] or [0]

    # Image metrics
    prods_with_imgs = len({img["product_id"] for img in images})
    imgs_per_prod = [sum(1 for img in images if img["product_id"] == p["product_id"]) for p in prods] or [0]
    color_mapped_imgs = sum(1 for img in images if img.get("color_name"))
    gallery_unmapped = len(images) - color_mapped_imgs

    # Content coverage
    desc_cov = sum(1 for p in prods if p.get("long_description"))
    comp_cov = sum(1 for p in prods if p.get("composition_text"))
    mat_cov = sum(1 for p in prods if p.get("material_text"))
    care_cov = sum(1 for p in prods if p.get("care_information"))
    fit_cov = sum(1 for p in prods if p.get("fit_information"))

    # Provenance
    hash_cov = sum(1 for p in prods if p.get("source_content_hash"))
    canon_cov = sum(1 for p in prods if p.get("canonical_url"))
    raw_cov = sum(1 for p in prods if f"{p.get('source_product_id', p['product_id'].split(':')[-1])}.json" in raw_files)

    # Sync readiness
    first_seen_cov = sum(1 for p in prods if p.get("first_seen_at"))
    last_seen_cov = sum(1 for p in prods if p.get("last_seen_at"))
    last_synced_cov = sum(1 for p in prods if p.get("last_synced_at"))
    lifecycle_cov = sum(1 for p in prods if p.get("lifecycle_status") == "ACTIVE")

    total_prods = len(prods) or 1

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "products": {
            "total_catalogue_queue": total_q,
            "complete": complete_count,
            "partial": partial_count,
            "failed_retryable": retryable_count,
            "failed_terminal": terminal_count,
            "queued_remaining": queued_count,
            "completion_percentage": round((complete_count / total_q) * 100, 2)
        },
        "pricing": {
            "products_with_price": len(with_price),
            "products_with_sale_price": len(sale_prods),
            "products_missing_price": len(missing_price),
            "price_conflicts": price_conflicts,
            "currency_distribution": dict(currencies),
            "price_history_records": len(price_hist)
        },
        "variants": {
            "total_variants": len(variants),
            "products_with_variants": prods_with_vars,
            "availability_distribution": dict(avail_dist),
            "avg_variants_per_product": round(statistics.mean(vars_per_prod), 2) if vars_per_prod else 0,
            "max_variants_per_product": max(vars_per_prod) if vars_per_prod else 0
        },
        "colors": {
            "total_colors": len(colors),
            "products_with_colors": prods_with_cols,
            "avg_colors_per_product": round(statistics.mean(cols_per_prod), 2) if cols_per_prod else 0,
            "max_colors_per_product": max(cols_per_prod) if cols_per_prod else 0
        },
        "images": {
            "total_normalized_images": len(images),
            "products_with_images": prods_with_imgs,
            "products_without_images": total_prods - prods_with_imgs,
            "color_linked_images": color_mapped_imgs,
            "gallery_unmapped_images": gallery_unmapped,
            "avg_images_per_product": round(statistics.mean(imgs_per_prod), 2) if imgs_per_prod else 0,
            "median_images_per_product": round(statistics.median(imgs_per_prod), 2) if imgs_per_prod else 0,
            "max_images_per_product": max(imgs_per_prod) if imgs_per_prod else 0
        },
        "content_coverage": {
            "description": f"{desc_cov}/{total_prods} ({desc_cov/total_prods*100:.1f}%)",
            "composition": f"{comp_cov}/{total_prods} ({comp_cov/total_prods*100:.1f}%)",
            "material": f"{mat_cov}/{total_prods} ({mat_cov/total_prods*100:.1f}%)",
            "care": f"{care_cov}/{total_prods} ({care_cov/total_prods*100:.1f}%)",
            "fit": f"{fit_cov}/{total_prods} ({fit_cov/total_prods*100:.1f}%)"
        },
        "provenance": {
            "raw_evidence_coverage": f"{raw_cov}/{total_prods} ({raw_cov/total_prods*100:.1f}%)",
            "content_hash_coverage": f"{hash_cov}/{total_prods} ({hash_cov/total_prods*100:.1f}%)",
            "canonical_url_coverage": f"{canon_cov}/{total_prods} ({canon_cov/total_prods*100:.1f}%)"
        },
        "sync_readiness": {
            "first_seen_at_coverage": f"{first_seen_cov}/{total_prods} ({first_seen_cov/total_prods*100:.1f}%)",
            "last_seen_at_coverage": f"{last_seen_cov}/{total_prods} ({last_seen_cov/total_prods*100:.1f}%)",
            "last_synced_at_coverage": f"{last_synced_cov}/{total_prods} ({last_synced_cov/total_prods*100:.1f}%)",
            "content_hash_coverage": f"{hash_cov}/{total_prods} ({hash_cov/total_prods*100:.1f}%)",
            "lifecycle_status_coverage": f"{lifecycle_cov}/{total_prods} ({lifecycle_cov/total_prods*100:.1f}%)"
        }
    }

    REPORTS.mkdir(parents=True, exist_ok=True)
    with open(REPORTS / 'phase_1c_final_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report


def run_scaling_pipeline(chunk_size=500, max_chunks=None):
    """Run full Phase 1C scaled pipeline."""
    print("\n==================================================")
    print("PHASE 1C — LARGE-SCALE CATALOGUE ENRICHMENT")
    print(f"Target Chunk Size: {chunk_size} products/chunk")
    print("==================================================\n")

    # Step 0: Ensure card resolution is executed
    print("Executing conservative card ID resolution pre-check...")
    execute_card_id_resolution(persist=True)

    # Initial validation
    val_init = validate_invariants()
    print(f"Initial validation PASS: {val_init}\n")

    chunk_idx = 1
    while True:
        if max_chunks and chunk_idx > max_chunks:
            print(f"Reached max chunks limit ({max_chunks}). Halting.")
            break

        # Check pending queue
        with open(STATE / 'product_detail_queue.json', 'r', encoding='utf-8') as f:
            queue = json.load(f)

        pending_queued = [q for q in queue if q.get("status") == "QUEUED"]
        if not pending_queued:
            print("No pending QUEUED products remaining!")
            break

        current_batch = pending_queued[:chunk_size]
        batch_ids = [item["id"] for item in current_batch]

        print(f"\n--------------------------------------------------")
        print(f"LAUNCHING CHUNK #{chunk_idx}: {len(batch_ids)} products ({len(pending_queued)} remaining queued)")
        print(f"--------------------------------------------------")

        results, metrics = run_enrichment_batch(
            product_ids=batch_ids,
            batch_size=len(batch_ids),
            preserve_completed=True
        )

        # Integrity Checks on the Chunk Output
        avg_imgs = metrics.get("images", {}).get("avg_images_per_product", 0)
        if avg_imgs > 15.0:
            print(f"[ANOMALY WARNING] Chunk #{chunk_idx} avg images {avg_imgs} > 15.0!")

        attempted = metrics.get("total_attempted", len(batch_ids))
        failed_count = metrics.get("total_failed_retryable", 0) + metrics.get("total_failed_terminal", 0)
        failure_rate = (failed_count / attempted) if attempted else 0
        if failure_rate > 0.10:
            raise InvariantViolationError(f"Chunk #{chunk_idx} failure rate {failure_rate*100:.1f}% exceeds 10% threshold!")

        # Validate invariants
        val_info = validate_invariants()
        print(f"\n[VALIDATION PASS] Chunk #{chunk_idx} passed all invariants.")
        print(f"  Cumulative Products: {val_info['normalized_products']} | Variants: {val_info['normalized_variants']} | Images: {val_info['normalized_images']}")

        # Record chunk report
        record_chunk_report(chunk_idx, metrics, val_info)
        generate_phase1c_final_report()

        chunk_idx += 1

    # Step 8: Legacy PARTIAL Migration
    with open(STATE / 'product_detail_queue.json', 'r', encoding='utf-8') as f:
        queue = json.load(f)
    pending_partial = [q for q in queue if q.get("status") == "PARTIAL"]

    if pending_partial:
        print(f"\n==================================================")
        print(f"STARTING LEGACY PARTIAL MIGRATION: {len(pending_partial)} records")
        print(f"==================================================\n")
        partial_ids = [p["id"] for p in pending_partial]
        p_results, p_metrics = run_enrichment_batch(
            product_ids=partial_ids,
            batch_size=len(partial_ids),
            preserve_completed=False  # Re-open to enrich
        )
        val_info = validate_invariants()
        print(f"[VALIDATION PASS] Legacy PARTIAL migration complete.")
        record_chunk_report("LEGACY_PARTIAL_MIGRATION", p_metrics, val_info)
        generate_phase1c_final_report()

    # Step 9: Final Failure Sweep for FAILED_RETRYABLE
    with open(STATE / 'product_detail_queue.json', 'r', encoding='utf-8') as f:
        queue = json.load(f)
    retryable = [q for q in queue if q.get("status") == "FAILED_RETRYABLE"]

    if retryable:
        print(f"\n==================================================")
        print(f"STARTING FINAL FAILURE SWEEP: {len(retryable)} retryable items")
        print(f"==================================================\n")
        retry_ids = [r["id"] for r in retryable]
        r_results, r_metrics = run_enrichment_batch(
            product_ids=retry_ids,
            batch_size=len(retry_ids),
            preserve_completed=False
        )
        val_info = validate_invariants()
        record_chunk_report("FAILURE_SWEEP", r_metrics, val_info)
        generate_phase1c_final_report()

    final_rep = generate_phase1c_final_report()
    print("\n==================================================")
    print("PHASE 1C LARGE SCALE ENRICHMENT COMPLETED!")
    print(f"Final Products Complete: {final_rep['products']['complete']} / {final_rep['products']['total_catalogue_queue']} ({final_rep['products']['completion_percentage']}%)")
    print("==================================================\n")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Phase 1C Large-Scale Scaling Runner")
    parser.add_argument("--chunk-size", type=int, default=500, help="Chunk size")
    parser.add_argument("--max-chunks", type=int, default=None, help="Maximum chunks to run in this execution")
    args = parser.parse_args()

    run_scaling_pipeline(chunk_size=args.chunk_size, max_chunks=args.max_chunks)
