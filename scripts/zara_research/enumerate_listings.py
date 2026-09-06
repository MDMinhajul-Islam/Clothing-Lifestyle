"""Phase 1B Product Enumeration Worker with Department Coverage Saturation.

Enumerates unique public products from verified product-bearing listings through
normal headed public-browser access (Microsoft Edge). Captures per-iteration scroll
traces, enforces conservative completion via category_end.py, maintains global unique
product registry and product-category relationships, and updates department coverage.
"""
import argparse
import csv
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/zara_research'))
from catalogue_progress import RAW, STATE, NORMAL, REPORTS, read, write, export
from repair_graph import canonicalize, department
from category_end import completion_reason

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
ENUM_DIR = RAW / 'enumeration'
MAJOR_DEPTS = ['WOMAN', 'MAN', 'KIDS', 'ZARA HOME', 'BEAUTY']


def extract_grid_state(page):
    """Extract product grid cards, data-productid values, product links and document metrics."""
    cards = page.query_selector_all(".product-grid-product, li.product-grid-product, [data-productid]")
    visible_cards = [c for c in cards if c.is_visible()]
    return page.evaluate(r"""() => {
        const cards = Array.from(document.querySelectorAll('.product-grid-product, li.product-grid-product, [data-productid]'));
        const visibleCards = cards.filter(c => {
            return !!(c.offsetWidth || c.offsetHeight || c.getClientRects().length);
        });
        const targetCards = visibleCards.length > 0 ? visibleCards : cards;

    seen_products = {}  # data_productid -> dict
    for c in (visible_cards if visible_cards else cards):
        pid = c.get_attribute("data-productid")
        if not pid:
            continue
        pid = pid.strip()
        const seenProducts = {};
        for (const c of targetCards) {
            const pid = c.getAttribute('data-productid');
            if (!pid) continue;
            const cleanPid = pid.trim();

        product_url = None
        commercial_token = None
        product_name = None
            let productUrl = null;
            let commercialToken = null;
            let productName = null;

        a_tag = c.query_selector("a[href*='-p']")
        if a_tag:
            href = a_tag.get_attribute("href") or ""
            if href:
                product_url = href.split('?')[0]
                p_match = re.search(r'-p(\d+)\.html', href)
                if p_match:
                    commercial_token = p_match[1]
            txt = a_tag.inner_text().strip()
            if txt:
                product_name = txt.split('\n')[0].strip()
            const aTag = c.querySelector("a[href*='-p']");
            if (aTag) {
                const href = aTag.getAttribute('href') || '';
                if (href) {
                    productUrl = href.split('?')[0];
                    const pMatch = href.match(/-p(\d+)\.html/);
                    if (pMatch) {
                        commercialToken = pMatch[1];
                    }
                }
                const txt = (aTag.innerText || '').trim();
                if (txt) {
                    productName = txt.split('\\n')[0].trim();
                }
            }

        if pid not in seen_products:
            seen_products[pid] = {
                "catalogue_id": pid,
                "commercial_ref_token": commercial_token,
                "product_url": product_url,
                "name": product_name
            if (!seenProducts[cleanPid]) {
                seenProducts[cleanPid] = {
                    catalogue_id: cleanPid,
                    commercial_ref_token: commercialToken,
                    product_url: productUrl,
                    name: productName
                };
            } else {
                if (!seenProducts[cleanPid].commercial_ref_token && commercialToken) {
                    seenProducts[cleanPid].commercial_ref_token = commercialToken;
                }
                if (!seenProducts[cleanPid].product_url && productUrl) {
                    seenProducts[cleanPid].product_url = productUrl;
                }
                if (!seenProducts[cleanPid].name && productName) {
                    seenProducts[cleanPid].name = productName;
                }
            }
        else:
            if not seen_products[pid]["commercial_ref_token"] and commercial_token:
                seen_products[pid]["commercial_ref_token"] = commercial_token
            if not seen_products[pid]["product_url"] and product_url:
                seen_products[pid]["product_url"] = product_url
            if not seen_products[pid]["name"] and product_name:
                seen_products[pid]["name"] = product_name
        }

    # Document metrics
    doc_height = page.evaluate("() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
    scroll_y = page.evaluate("() => window.scrollY || window.pageYOffset")
    inner_height = page.evaluate("() => window.innerHeight")
    at_bottom = bool((scroll_y + inner_height) >= (doc_height - 180))
        const docHeight = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
        const scrollY = window.scrollY || window.pageYOffset;
        const innerHeight = window.innerHeight;
        const atBottom = Boolean((scrollY + innerHeight) >= (docHeight - 180));

    # Loading indicators
    loading_active = False
    try:
        loading_active = page.evaluate("""() => {
        let loadingActive = false;
        try {
            const spinners = document.querySelectorAll('.loading, .spinner, [aria-busy="true"], [class*="loading-indicator"]');
            for (let s of spinners) {
                if (s.offsetParent !== null) return true;
            for (const s of spinners) {
                if (s.offsetParent !== null) {
                    loadingActive = true;
                    break;
                }
            }
            return false;
        }""")
    except Exception:
        pass
        } catch (e) {}

    # Load more control
    load_more_active = False
    try:
        load_more_btn = page.query_selector("button.load-more-products, button[class*='load-more' i], a[class*='load-more' i]")
        if load_more_btn and load_more_btn.is_visible():
            load_more_active = True
    except Exception:
        pass
        let loadMoreActive = false;
        try {
            const loadMoreBtn = document.querySelector("button.load-more-products, button[class*='load-more' i], a[class*='load-more' i]");
            if (loadMoreBtn && (loadMoreBtn.offsetWidth || loadMoreBtn.offsetHeight || loadMoreBtn.getClientRects().length)) {
                loadMoreActive = true;
            }
        } catch (e) {}

    return {
        "visible_cards_count": len(visible_cards),
        "products": seen_products,
        "doc_height": doc_height,
        "at_bottom": at_bottom,
        "loading": loading_active,
        "load_more_available": load_more_active
    }
        return {
            visible_cards_count: targetCards.length,
            products: seenProducts,
            doc_height: docHeight,
            at_bottom: atBottom,
            loading: loadingActive,
            load_more_available: loadMoreActive
        };
    }""")


def scroll_listing(page, max_iterations=30, idle_timeout_ms=2500):
def scroll_listing(page, max_iterations=60, idle_timeout_ms=2500):
def scroll_listing(page, max_iterations=80, idle_timeout_ms=2000, prior_seen_ids=None):
    """Incrementally scrolls a listing page and evaluates conservative category-end conditions."""
    observations = []
    seen_products_by_id = {}
    prior_seen_set = set(prior_seen_ids) if prior_seen_ids else set()

    # Observation 0 (settled initial view)
    state = extract_grid_state(page)
    seen_products_by_id.update(state["products"])
    cumulative_now = prior_seen_set.union(seen_products_by_id.keys())

    obs_0 = {
        "scroll_iteration": 0,
        "at_bottom": state["at_bottom"],
        "settled": True,
        "new_unique_products": len(state["products"]),
        "products_seen": len(seen_products_by_id),
        "products_seen": len(cumulative_now),
        "document_height": state["doc_height"],
        "loading": state["loading"],
        "load_more_available": state["load_more_available"],
        "technical_restriction": False,
        "error": None,
        "explicit_empty": (len(state["products"]) == 0 and state["at_bottom"]),
        "explicit_end": False
    }
    observations.append(obs_0)

    reason = completion_reason(observations)
    if reason:
        return reason, observations, seen_products_by_id

    for iteration in range(1, max_iterations + 1):
        # Click load more if present
        if state["load_more_available"]:
            try:
                btn = page.query_selector("button.load-more-products, button[class*='load-more' i], a[class*='load-more' i]")
                if btn and btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(1500)
            except Exception:
                pass

        # Scroll down smoothly
        page.evaluate("() => window.scrollBy(0, Math.floor(window.innerHeight * 1.5))")
        # Scroll down progressively
        page.evaluate("() => window.scrollBy(0, Math.floor(window.innerHeight * 2.5))")
        page.wait_for_timeout(idle_timeout_ms)

        # If nearing bottom or height is stable, ensure we reach the absolute bottom to trigger final intersection observers
        cur_scroll_y = page.evaluate("() => window.scrollY || window.pageYOffset")
        cur_inner_h = page.evaluate("() => window.innerHeight")
        cur_doc_h = page.evaluate("() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
        if (cur_scroll_y + cur_inner_h) >= (cur_doc_h - 1500):
            page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
            page.wait_for_timeout(1000)

        state = extract_grid_state(page)
        new_ids = set(state["products"].keys()) - set(seen_products_by_id.keys())
        seen_products_by_id.update(state["products"])
        cumulative_now = prior_seen_set.union(seen_products_by_id.keys())

        obs = {
            "scroll_iteration": iteration,
            "at_bottom": state["at_bottom"],
            "settled": True,
            "new_unique_products": len(new_ids),
            "products_seen": len(seen_products_by_id),
            "products_seen": len(cumulative_now),
            "document_height": state["doc_height"],
            "loading": state["loading"],
            "load_more_available": state["load_more_available"],
            "technical_restriction": False,
            "error": None,
            "explicit_empty": False,
            "explicit_end": False
        }
        observations.append(obs)

        reason = completion_reason(observations)
        if reason:
            return reason, observations, seen_products_by_id

    return "NO_NEW_PRODUCTS", observations, seen_products_by_id
    # If safety maximum iteration reached without category_end completion:
    return "PARTIAL_MAX_ITERATIONS", observations, seen_products_by_id


def build_department_coverage(enum_queue, unique_products, graph, discovery_queue, product_categories, current_batch_results):
    """Compute comprehensive department coverage metrics across all major departments."""
    nodes = graph.get("nodes", [])
    nodes_by_dept = {d: [n for n in nodes if n.get("department") == d] for d in MAJOR_DEPTS}

    # Count verified listings and completed listings per department
    enum_by_dept = {d: [] for d in MAJOR_DEPTS}
    for item in enum_queue:
        d = department(item["url"])
        if d in enum_by_dept:
            enum_by_dept[d].append(item)

    # Count unique products per department
    prods_by_dept = {d: set() for d in MAJOR_DEPTS}
    for p in unique_products:
        for cat_url in p.get("categories_seen_in", []):
            d = department(cat_url)
            if d in prods_by_dept:
                prods_by_dept[d].add(p["product_id"])

    # Duplicate appearances per department
    appearances_by_dept = {d: 0 for d in MAJOR_DEPTS}
    for rel in product_categories:
        d = department(rel.get("category_url", ""))
        if d in appearances_by_dept:
            appearances_by_dept[d] += 1

    # New unique products in current batch per department
    new_in_batch_by_dept = {d: 0 for d in MAJOR_DEPTS}
    for res in current_batch_results:
        d = res.get("department")
        if d in new_in_batch_by_dept:
            new_in_batch_by_dept[d] += res.get("new_global_unique_products", 0)

    # Remaining high value structural routes (QUEUED in discovery queue, not deferred SEO)
    disc_queued_by_dept = {d: 0 for d in MAJOR_DEPTS}
    for q in discovery_queue:
        if q.get("status") == "QUEUED":
            d = department(q.get("url", ""))
            if d in disc_queued_by_dept:
                disc_queued_by_dept[d] += 1

    coverage = {}
    for d in MAJOR_DEPTS:
        structural_count = len(nodes_by_dept[d])
        verified_count = len(enum_by_dept[d])
        completed_count = sum(1 for item in enum_by_dept[d] if item.get("status") == "COMPLETE")
        partial_count = sum(1 for item in enum_by_dept[d] if item.get("status") == "PARTIAL")
        queued_count = sum(1 for item in enum_by_dept[d] if item.get("status") == "QUEUED")
        unique_seen = len(prods_by_dept[d])
        total_apps = appearances_by_dept[d]
        dups = max(0, total_apps - unique_seen)
        remaining_structural = disc_queued_by_dept[d]
        tech_restrictions = sum(1 for item in enum_by_dept[d] if item.get("status") == "TECHNICAL_RESTRICTION")

        # Determine status
        if tech_restrictions > 0:
            status = "PARTIAL_TECHNICAL_RESTRICTION"
        elif completed_count == verified_count and remaining_structural == 0 and unique_seen > 0:
            status = "SATURATED"
        elif completed_count == verified_count and unique_seen > 0:
            status = "NEAR_SATURATION"
        else:
            status = "ACTIVE"

        coverage[d] = {
            "department": d,
            "structural_listing_count": structural_count,
            "verified_listing_count": verified_count,
            "completed_listing_count": completed_count,
            "partial_listing_count": partial_count,
            "queued_listing_count": queued_count,
            "unique_products_seen": unique_seen,
            "new_unique_products_last_batch": new_in_batch_by_dept[d],
            "duplicate_product_appearances": dups,
            "remaining_high_value_structural_routes": remaining_structural,
            "technical_restrictions": tech_restrictions,
            "coverage_status": status
        }

    return coverage


def run_enumeration(batch_size=3, category_ids=None):
def run_enumeration(batch_size=3, category_ids=None, max_iterations=80):
    """Executes Phase 1B product enumeration for a selected batch of verified listings."""
    ENUM_DIR.mkdir(parents=True, exist_ok=True)

    # Load persistent state
    enum_queue = read(STATE / 'category_enumeration_queue.json', [])
    unique_products = read(STATE / 'unique_products.json', [])
    product_detail_queue = read(STATE / 'product_detail_queue.json', [])
    product_categories = read(STATE / 'product_categories.json')
    if product_categories is None:
        product_categories = read(NORMAL / 'product_categories.json', [])
    discovery_queue = read(STATE / 'category_discovery_queue.json', [])
    graph = read(STATE / 'category_graph.json', {"nodes": [], "edges": []})

    # Global index of unique products
    existing_by_sku = {}
    existing_by_card_id = {}
    for p in unique_products:
        pid = p["product_id"]
        sku = p.get("source_product_id")
        if sku:
            existing_by_sku[sku] = p
        for cid in p.get("public_card_ids", []):
            existing_by_card_id[str(cid)] = p

    # Existing detail queue IDs
    detail_queue_ids = {q["id"] for q in product_detail_queue}

    # Existing product-category relationship keys
    existing_rel_keys = {(r.get("product_id"), r.get("category_id")) for r in product_categories}

    # Global counts before run
    global_unique_before = len(unique_products)
    detail_queue_before = len(product_detail_queue)
    enum_completed_before = sum(1 for item in enum_queue if item.get("status") == "COMPLETE")
    enum_remaining_before = len(enum_queue) - enum_completed_before

    # Select batch
    queued_items = [q for q in enum_queue if q.get("status") == "QUEUED"]
    if category_ids:
        target_set = set(category_ids)
        batch = [q for q in queued_items if q["id"] in target_set]
        id_to_item = {q["id"]: q for q in enum_queue}
        batch = []
        for cid in category_ids:
            if cid in id_to_item:
                batch.append(id_to_item[cid])
            else:
                print(f"Warning: category ID {cid} not found in enumeration queue.")
    else:
        batch = queued_items[:batch_size]

    if not batch:
        print("No pending listings in enumeration queue matching criteria.")
        return [], {}

    print(f"\n==================================================")
    print(f"STARTING PHASE 1B PRODUCT ENUMERATION: {len(batch)} listings")
    print(f"Verified listings total: {len(enum_queue)} (Pending: {len(queued_items)})")
    print(f"Global unique products before batch: {global_unique_before}")
    print(f"==================================================\n")

    batch_results = []
    total_batch_new_products = 0
    total_batch_duplicate_appearances = 0
    total_batch_appearances = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=EDGE_PATH,
            headless=False
        )
        context = browser.new_context()

        for idx, item in enumerate(batch, 1):
            cat_id = item["id"]
            url = item["url"]
            dept = department(url)
            start_time = time.time()
            now_iso = datetime.now(timezone.utc).isoformat()
            previous_status = item.get("status", "QUEUED")
            prior_seen_ids = set(item.get("seen_product_ids", []))
            prior_seen_count = len(prior_seen_ids)

            print(f"[{idx}/{len(batch)}] Enumerating {cat_id} | {dept} | {url}")
            print(f"[{idx}/{len(batch)}] Enumerating {cat_id} | {dept} | {previous_status} ({prior_seen_count} prior IDs) | {url}")
            page = context.new_page()

            error_msg = None
            reason = "UNKNOWN"
            observations = []
            seen_products = {}

            try:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
                page.wait_for_timeout(3500)

                # Dismiss cookie banner if present
                try:
                    accept_btn = page.query_selector("#onetrust-accept-btn-handler, button#onetrust-accept-btn-handler")
                    if accept_btn and accept_btn.is_visible():
                        accept_btn.click()
                        page.wait_for_timeout(1000)
                except Exception:
                    pass

                # Check technical restrictions
                page_title = page.title().strip()
                if "access denied" in page_title.lower():
                    reason = "TECHNICAL_RESTRICTION"
                    error_msg = "Access Denied title detected"
                else:
                    reason, observations, seen_products = scroll_listing(page)
                    reason, observations, seen_products = scroll_listing(
                        page, max_iterations=max_iterations, idle_timeout_ms=2000, prior_seen_ids=prior_seen_ids
                    )

            except Exception as e:
                error_msg = str(e)
                reason = "ERROR"
                print(f"   ERROR: {error_msg}")
            finally:
                page.close()

            elapsed_seconds = round(time.time() - start_time, 2)
            print(f"   -> Completed: {reason} in {len(observations)-1} scrolls ({elapsed_seconds}s), seen IDs: {len(seen_products)}")
            cumulative_seen_ids = prior_seen_ids.union(seen_products.keys())
            new_ids_this_run = len(cumulative_seen_ids) - len(prior_seen_ids)
            print(f"   -> Result: {reason} in {len(observations)-1} scrolls ({elapsed_seconds}s) | Seen this run: {len(seen_products)} | Cumulative IDs: {len(cumulative_seen_ids)} (+{new_ids_this_run} new to listing)")

            # Process discovered products
            initial_obs = observations[0] if observations else {}
            initial_count = initial_obs.get("new_unique_products", 0)

            listing_new_products = 0
            listing_duplicates = 0
            new_rel_count = 0
            existing_rel_count = 0
            new_detail_queue_count = 0

            for pid, p_info in seen_products.items():
                total_batch_appearances += 1
                commercial_token = p_info.get("commercial_ref_token")
                p_url = p_info.get("product_url")
                p_name = p_info.get("name")

                # Match against global registry
                matched_p = None
                if commercial_token and commercial_token in existing_by_sku:
                    matched_p = existing_by_sku[commercial_token]
                elif pid in existing_by_card_id:
                    matched_p = existing_by_card_id[pid]

                if matched_p:
                    # Duplicate appearance
                    listing_duplicates += 1
                    total_batch_duplicate_appearances += 1
                    matched_p["last_seen_at"] = now_iso
                    if url not in matched_p.setdefault("categories_seen_in", []):
                        matched_p["categories_seen_in"].append(url)
                    if pid not in matched_p.setdefault("public_card_ids", []):
                        matched_p["public_card_ids"].append(pid)
                    final_product_id = matched_p["product_id"]
                    final_src_id = matched_p.get("source_product_id", commercial_token or pid)
                else:
                    # New unique product
                    listing_new_products += 1
                    total_batch_new_products += 1

                    if commercial_token:
                        final_product_id = f"zara-us:{commercial_token}"
                        final_src_id = commercial_token
                    else:
                        final_product_id = f"zara-us:card-{pid}"
                        final_src_id = pid

                    new_p_record = {
                        "product_id": final_product_id,
                        "source_product_id": final_src_id,
                        "product_group_id": final_src_id,
                        "identity_basis": "Listing grid data-productid and anchor commercial ref",
                        "product_url": p_url,
                        "first_seen_category": url,
                        "categories_seen_in": [url],
                        "first_seen_at": now_iso,
                        "last_seen_at": now_iso,
                        "extraction_status": "QUEUED",
                        "missing_detail_fields": [],
                        "public_card_ids": [pid],
                        "full_detail_extraction_status": "QUEUED_FOR_PHASE_1C"
                    }
                    unique_products.append(new_p_record)
                    if commercial_token:
                        existing_by_sku[commercial_token] = new_p_record
                    existing_by_card_id[pid] = new_p_record

                    # Queue for Phase 1C detail extraction
                    if final_product_id not in detail_queue_ids:
                        product_detail_queue.append({
                            "id": final_product_id,
                            "url": p_url,
                            "status": "QUEUED",
                            "attempt_count": 0,
                            "last_attempt_at": None,
                            "error": None,
                            "checkpoint": {
                                "core_preserved": False,
                                "supplemental_only": False,
                                "requires_validation_before_reopen": False,
                                "source_category_id": cat_id
                            }
                        })
                        detail_queue_ids.add(final_product_id)
                        new_detail_queue_count += 1

                # Product-Category relationship
                rel_key = (final_product_id, cat_id)
                if rel_key not in existing_rel_keys:
                    product_categories.append({
                        "product_id": final_product_id,
                        "source_product_id": final_src_id,
                        "category_id": cat_id,
                        "category_url": url,
                        "first_seen_at": now_iso,
                        "last_seen_at": now_iso,
                        "enumeration_source": "PHASE_1B_LISTING_SCROLL"
                    })
                    existing_rel_keys.add(rel_key)
                    new_rel_count += 1
                else:
                    existing_rel_count += 1

            # Save raw trace document
            token_match = re.search(r'-(?:l|mkt|c)(\d+)\.html(?:\?page=(\d+))?', url)
            if token_match:
                token = token_match[1]
                if token_match[2]:
                    token = f"{token}_p{token_match[2]}"
            else:
                token = hashlib.sha256(url.encode()).hexdigest()[:16]

            listing_status = "COMPLETE" if reason in ["NO_NEW_PRODUCTS", "END_OF_LIST", "CATEGORY_EMPTY"] else ("PARTIAL" if reason == "PARTIAL_MAX_ITERATIONS" else ("TECHNICAL_RESTRICTION" if reason == "TECHNICAL_RESTRICTION" else "ERROR"))
            listing_status = (
                "COMPLETE" if reason in ["NO_NEW_PRODUCTS", "END_OF_LIST", "CATEGORY_EMPTY"]
                else ("PARTIAL" if reason == "PARTIAL_MAX_ITERATIONS"
                else ("TECHNICAL_RESTRICTION" if reason == "TECHNICAL_RESTRICTION"
                else "ERROR"))
            )

            raw_trace_file = ENUM_DIR / f"{token}.json"
            raw_doc = {
                "category_id": cat_id,
                "category_url": url,
                "department": dept,
                "started_at": now_iso,
                "elapsed_seconds": elapsed_seconds,
                "status": "COMPLETE" if reason in ["NO_NEW_PRODUCTS", "END_OF_LIST", "CATEGORY_EMPTY"] else ("TECHNICAL_RESTRICTION" if reason == "TECHNICAL_RESTRICTION" else "ERROR"),
                "previous_status": previous_status,
                "previous_seen_count": prior_seen_count,
                "seen_this_run": len(seen_products),
                "cumulative_unique_products_seen": len(cumulative_seen_ids),
                "new_ids_to_listing": new_ids_this_run,
                "status": listing_status,
                "completion_reason": reason,
                "error": error_msg,
                "initial_products_count": initial_count,
                "total_unique_products_seen": len(seen_products),
                "new_global_unique_products": listing_new_products,
                "duplicate_appearances": listing_duplicates,
                "new_category_relationships": new_rel_count,
                "existing_category_relationships": existing_rel_count,
                "final_bottom_state": observations[-1].get("at_bottom") if observations else False,
                "scroll_trace": observations,
                "products_sample": list(seen_products.values())[:10]
            }
            write(raw_trace_file, raw_doc)

            # Update item in enumeration queue
            item["status"] = raw_doc["status"]
            item["status"] = listing_status
            item["attempt_count"] = item.get("attempt_count", 0) + 1
            item["last_attempt_at"] = now_iso
            item["error"] = error_msg
            item["scroll_iteration"] = len(observations) - 1
            item["seen_product_ids"] = list(seen_products.keys())
            item["seen_product_ids"] = list(cumulative_seen_ids)
            item["completion_reason"] = reason
            item["checkpoint"] = {
                "phase": "enumeration",
                "scroll_iteration": len(observations) - 1,
                "seen_product_ids": list(seen_products.keys()),
                "seen_product_ids": list(cumulative_seen_ids),
                "completion_reason": reason,
                "evidence_file": str(raw_trace_file.relative_to(ROOT))
            }

            # Update category node in graph
            for n in graph.get("nodes", []):
                if n.get("category_id") == cat_id:
                    n["enumeration_complete"] = (item["status"] == "COMPLETE")
                    n["last_verified_at"] = now_iso

            # Atomic persistence after each listing
            write(STATE / 'category_enumeration_queue.json', enum_queue)
            write(STATE / 'unique_products.json', unique_products)
            write(STATE / 'product_detail_queue.json', product_detail_queue)
            write(STATE / 'product_categories.json', product_categories)
            export(NORMAL, 'product_categories', product_categories, ['product_id', 'category_id', 'category_url'])
            write(STATE / 'category_graph.json', graph)

            # Record listing summary
            batch_results.append({
                "category_id": cat_id,
                "department": dept,
                "url": url,
                "previous_status": previous_status,
                "previous_seen_count": prior_seen_count,
                "seen_this_run": len(seen_products),
                "new_ids_this_run": new_ids_this_run,
                "final_total_ids": len(cumulative_seen_ids),
                "final_status": listing_status,
                "completion_reason": reason,
                "initial_product_ids": initial_count,
                "scroll_iterations": len(observations) - 1,
                "observations_trace": observations,
                "final_unique_products": len(seen_products),
                "completion_reason": reason,
                "duplicate_appearances": listing_duplicates,
                "new_global_unique_products": listing_new_products,
                "new_product_category_relationships": new_rel_count,
                "existing_product_category_relationships": existing_rel_count,
                "new_product_detail_queue_items": new_detail_queue_count,
                "final_bottom_state": observations[-1].get("at_bottom") if observations else False,
                "elapsed_seconds": elapsed_seconds,
                "error_or_restriction": error_msg
            })

        browser.close()

    # Generate updated department coverage
    dept_coverage = build_department_coverage(
        enum_queue, unique_products, graph, discovery_queue, product_categories, batch_results
    )

    # Export coverage reports
    coverage_summary = {
        "phase": "PHASE_1B_PRODUCT_ENUMERATION",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "listings_enumerated_in_batch": len(batch_results),
        "global_unique_products_before": global_unique_before,
        "global_unique_products_after": len(unique_products),
        "new_unique_products_discovered": total_batch_new_products,
        "total_product_appearances": total_batch_appearances,
        "duplicate_product_appearances": total_batch_duplicate_appearances,
        "unique_product_yield": round(total_batch_new_products / len(batch_results), 2) if batch_results else 0.0,
        "duplicate_ratio": round(total_batch_duplicate_appearances / total_batch_appearances, 4) if total_batch_appearances else 0.0,
        "enumeration_queue_completed": sum(1 for item in enum_queue if item.get("status") == "COMPLETE"),
        "enumeration_queue_partial": sum(1 for item in enum_queue if item.get("status") == "PARTIAL"),
        "enumeration_queue_queued": sum(1 for item in enum_queue if item.get("status") == "QUEUED"),
        "enumeration_queue_remaining": sum(1 for item in enum_queue if item.get("status") != "COMPLETE"),
        "product_detail_queue_size": len(product_detail_queue),
        "departments": dept_coverage
    }
    write(REPORTS / 'zara_department_coverage.json', coverage_summary)

    # Markdown report
    md_report = f"# Zara Department Catalogue Coverage (Phase 1B)\n\n"
    md_report += f"**Updated**: {coverage_summary['updated_at']} | **Phase**: {coverage_summary['phase']}\n\n"
    md_report += f"| Department | Structural Listings | Verified Listings | Completed Listings | Unique Products | New in Last Batch | Duplicate Appearances | Remaining Structural Queue | Tech Restrictions | Coverage Status |\n"
    md_report += f"|---|---:|---:|---:|---:|---:|---:|---:|---:|---|\n"
    md_report += f"| Department | Structural Listings | Verified Listings | Completed Listings | Partial Listings | Queued Listings | Unique Products | New in Last Batch | Duplicate Appearances | Remaining Structural Queue | Tech Restrictions | Coverage Status |\n"
    md_report += f"|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|\n"
    for d, c in dept_coverage.items():
        md_report += f"| **{d}** | {c['structural_listing_count']} | {c['verified_listing_count']} | {c['completed_listing_count']} | {c['unique_products_seen']} | {c['new_unique_products_last_batch']} | {c['duplicate_product_appearances']} | {c['remaining_high_value_structural_routes']} | {c['technical_restrictions']} | `{c['coverage_status']}` |\n"
        md_report += f"| **{d}** | {c['structural_listing_count']} | {c['verified_listing_count']} | {c['completed_listing_count']} | {c['partial_listing_count']} | {c['queued_listing_count']} | {c['unique_products_seen']} | {c['new_unique_products_last_batch']} | {c['duplicate_product_appearances']} | {c['remaining_high_value_structural_routes']} | {c['technical_restrictions']} | `{c['coverage_status']}` |\n"

    md_report += f"\n## Global Summary\n"
    md_report += f"- **Global Unique Products**: {coverage_summary['global_unique_products_after']} (+{coverage_summary['new_unique_products_discovered']} new in batch)\n"
    md_report += f"- **Unique Product Yield**: {coverage_summary['unique_product_yield']} new products/listing\n"
    md_report += f"- **Duplicate Ratio**: {coverage_summary['duplicate_ratio'] * 100:.2f}%\n"
    md_report += f"- **Enumeration Queue**: {coverage_summary['enumeration_queue_completed']} completed / {coverage_summary['enumeration_queue_remaining']} remaining\n"
    md_report += f"- **Enumeration Queue**: {coverage_summary['enumeration_queue_completed']} completed / {coverage_summary['enumeration_queue_partial']} partial / {coverage_summary['enumeration_queue_queued']} queued\n"
    md_report += f"- **Product Detail Queue Size**: {coverage_summary['product_detail_queue_size']} items queued for Phase 1C\n"

    (REPORTS / 'zara_department_coverage.md').write_text(md_report, encoding='utf-8')

    return batch_results, coverage_summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Phase 1B Listing Product Enumerator")
    parser.add_argument("--batch-size", type=int, default=3, help="Batch size to enumerate")
    parser.add_argument("--category-ids", type=str, default=None, help="Comma-separated category IDs to enumerate")
    parser.add_argument("--max-iterations", type=int, default=80, help="Max scroll iterations per listing")
    args = parser.parse_args()

    cat_ids = [c.strip() for c in args.category_ids.split(",") if c.strip()] if args.category_ids else None
    results, summary = run_enumeration(batch_size=args.batch_size, category_ids=cat_ids)
    results, summary = run_enumeration(batch_size=args.batch_size, category_ids=cat_ids, max_iterations=args.max_iterations)
    print(f"\nBatch finished: {len(results)} listings processed.")

