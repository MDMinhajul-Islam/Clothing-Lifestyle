"""Card ID Resolution Module for Zara US Catalogue.

Conservatively resolves listing-card identities (zara-us:card-*)
to canonical public product identities using persisted evidence.
If unresolvable without public URL/evidence, classifies as FAILED_TERMINAL
with reason 'UNRESOLVED_LISTING_CARD_IDENTITY'.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / 'data/zara'


def extract_url_token(url):
    """Extract canonical numeric/alphanumeric product token from Zara product URL."""
    if not url:
        return None
    m = re.search(r'-p(?:T)?(\d+)\.html', url)
    return m.group(1) if m else None


def resolve_single_card_identity(card_id, url=None, unique_products_map=None, alias_map=None):
    """Attempt conservative resolution of a single card identity.
    
    Returns:
        dict: {
            "legacy_card_id": card_id,
            "canonical_product_id": canonical_id or None,
            "status": "RESOLVED" or "UNRESOLVED",
            "evidence": description of evidence or None,
            "failure_reason": reason string if unresolved
        }
    """
    if not card_id.startswith("zara-us:card-"):
        return {
            "legacy_card_id": card_id,
            "canonical_product_id": card_id,
            "status": "RESOLVED",
            "evidence": "IDENTITY_ALREADY_CANONICAL",
            "failure_reason": None
        }

    raw_cid = card_id.replace("zara-us:card-", "")
    unique_products_map = unique_products_map or {}
    alias_map = alias_map or {}

    # 1. Existing alias mapping
    if card_id in alias_map:
        return {
            "legacy_card_id": card_id,
            "canonical_product_id": alias_map[card_id].get("canonical_product_id"),
            "status": "RESOLVED",
            "evidence": "PERSISTED_ALIAS_MAP",
            "failure_reason": None
        }

    # 2. Check if raw card ID matches an existing canonical product source_product_id
    canonical_match_id = f"zara-us:{raw_cid}"
    if canonical_match_id in unique_products_map:
        return {
            "legacy_card_id": card_id,
            "canonical_product_id": canonical_match_id,
            "status": "RESOLVED",
            "evidence": f"SOURCE_PRODUCT_ID_MATCH:{raw_cid}",
            "failure_reason": None
        }

    # 3. Check public_card_ids inside known canonical products
    for pid, p in unique_products_map.items():
        if pid.startswith("zara-us:card-"):
            continue
        if raw_cid in p.get("public_card_ids", []):
            return {
                "legacy_card_id": card_id,
                "canonical_product_id": pid,
                "status": "RESOLVED",
                "evidence": f"PUBLIC_CARD_ID_ASSOCIATION:{pid}",
                "failure_reason": None
            }

    # 4. Check direct product URL
    if url:
        token = extract_url_token(url)
        if token:
            candidate_pid = f"zara-us:{token}"
            if candidate_pid in unique_products_map:
                return {
                    "legacy_card_id": card_id,
                    "canonical_product_id": candidate_pid,
                    "status": "RESOLVED",
                    "evidence": f"URL_TOKEN_MATCH_CANONICAL:{candidate_pid}",
                    "failure_reason": None
                }
            else:
                # Direct public URL exists and exposes distinct product token
                return {
                    "legacy_card_id": card_id,
                    "canonical_product_id": candidate_pid,
                    "status": "RESOLVED",
                    "evidence": f"DIRECT_URL_TOKEN:{token}",
                    "failure_reason": None
                }

    # 5. Cannot resolve without guessing or fabricating
    return {
        "legacy_card_id": card_id,
        "canonical_product_id": None,
        "status": "UNRESOLVED",
        "evidence": None,
        "failure_reason": "UNRESOLVED_LISTING_CARD_IDENTITY"
    }


def execute_card_id_resolution(persist=True):
    """Process all card items in product_detail_queue and persist resolution mapping."""
    queue_file = STATE / 'product_detail_queue.json'
    unique_file = STATE / 'unique_products.json'
    resolutions_file = STATE / 'card_id_resolutions.json'

    with open(queue_file, 'r', encoding='utf-8') as f:
        queue = json.load(f)

    with open(unique_file, 'r', encoding='utf-8') as f:
        unique_prods = json.load(f)

    unique_map = {p["product_id"]: p for p in unique_prods}

    # Load existing resolutions if present
    existing_resolutions = {}
    if resolutions_file.exists():
        with open(resolutions_file, 'r', encoding='utf-8') as f:
            for r in json.load(f):
                existing_resolutions[r["legacy_card_id"]] = r

    now_iso = datetime.now(timezone.utc).isoformat()
    resolutions = []
    unresolved_terminal_count = 0
    resolved_count = 0
    already_complete_count = 0

    for item in queue:
        qid = item["id"]
        if not qid.startswith("zara-us:card-"):
            continue

        if item.get("status") == "COMPLETE":
            already_complete_count += 1
            res = resolve_single_card_identity(qid, item.get("url"), unique_map, existing_resolutions)
            res["resolved_at"] = item.get("last_attempt_at") or now_iso
            res["queue_status"] = "COMPLETE"
            resolutions.append(res)
            continue

        res = resolve_single_card_identity(qid, item.get("url"), unique_map, existing_resolutions)
        res["resolved_at"] = now_iso

        if res["status"] == "UNRESOLVED":
            item["status"] = "FAILED_TERMINAL"
            item["error"] = res["failure_reason"]
            item["last_attempt_at"] = now_iso
            res["queue_status"] = "FAILED_TERMINAL"
            unresolved_terminal_count += 1
        else:
            resolved_count += 1
            res["queue_status"] = item.get("status")

        resolutions.append(res)

    if persist:
        # Atomic write of resolutions
        resolutions_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_res = resolutions_file.with_suffix('.tmp')
        tmp_res.write_text(json.dumps(resolutions, indent=2, ensure_ascii=False), encoding='utf-8')
        tmp_res.replace(resolutions_file)

        # Atomic write of queue
        tmp_q = queue_file.with_suffix('.tmp')
        tmp_q.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding='utf-8')
        tmp_q.replace(queue_file)

    report = {
        "total_card_items": len(resolutions),
        "already_complete": already_complete_count,
        "resolved_items": resolved_count,
        "unresolved_terminal": unresolved_terminal_count,
        "queue_total": len(queue)
    }
    return resolutions, report


if __name__ == '__main__':
    res, rep = execute_card_id_resolution(persist=True)
    print("Card ID Resolution Report:")
    print(json.dumps(rep, indent=2))
