"""Small-batch category classification worker for Phase 1A.

Processes a controlled batch (default 5) of QUEUED category discovery routes
using normal public browser access with Microsoft Edge.
Captures rich DOM evidence, classifies each route conservatively, persists state
atomically, updates the persistent graph and queues, and runs validation.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/zara_research'))
from catalogue_progress import RAW, STATE, read, write
from repair_graph import canonicalize, department, category_route, build as repair_graph_build

DISCOVERY_DIR = RAW / 'discovery'
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def extract_page_evidence(page, url):
    page.goto(url, timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(3500)

    # Dismiss nonbinding privacy/cookie banner if present
    try:
        accept_btn = page.query_selector("#onetrust-accept-btn-handler, button#onetrust-accept-btn-handler")
        if accept_btn and accept_btn.is_visible():
            accept_btn.click()
            page.wait_for_timeout(1000)
    except Exception:
        pass

    final_url = page.url
    page_title = page.title().strip()

    # Check for security challenges or restrictions
    body_text = ""
    try:
        body_text = page.inner_text("body")[:3000]
    except Exception:
        pass

    restriction = False
    restriction_reason = None
    if "Access Denied" in page_title or "access denied" in page_title.lower():
        restriction = True
        restriction_reason = "Title contains 'Access Denied'"
    elif any(k in body_text.lower() for k in ["verify you are human", "security check", "challenge-running", "cf-turnstile"]):
        restriction = True
        restriction_reason = "Verification challenge detected in page markup"

    # Headings
    headings = []
    for h in page.query_selector_all("h1, h2, h3"):
        txt = h.inner_text().strip()
        if txt and txt not in headings:
            headings.append(txt)
    main_heading = headings[0] if headings else None

    # JSON-LD Structured Data
    jsonld_raw = []
    jsonld_types = []
    for s in page.query_selector_all('script[type="application/ld+json"]'):
        try:
            data = json.loads(s.inner_text())
            jsonld_raw.append(data)
            if isinstance(data, dict):
                t = data.get('@type')
                if t and t not in jsonld_types:
                    jsonld_types.append(t)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        t = item.get('@type')
                        if t and t not in jsonld_types:
                            jsonld_types.append(t)
        except Exception:
            pass

    # Canonical link
    canonical = None
    try:
        canon_el = page.query_selector('link[rel="canonical"]')
        if canon_el:
            canonical = canon_el.get_attribute("href")
    except Exception:
        pass

    # Product cards and product links
    grid_cards = page.query_selector_all(".product-grid-product, li.product-grid-product")
    if not grid_cards:
        grid_cards = page.query_selector_all("[data-productid]")
    visible_cards = [c for c in grid_cards if c.is_visible()]
    card_count = len(visible_cards) if visible_cards else len(grid_cards)

    catalogue_product_ids = set()
    product_links = set()
    commercial_ref_tokens = set()

    for c in grid_cards:
        pid = c.get_attribute("data-productid")
        if pid:
            catalogue_product_ids.add(pid)
        for a in c.query_selector_all("a[href*='-p']"):
            href = a.get_attribute("href") or ""
            p_match = re.search(r'-p(\d+)\.html', href)
            if p_match:
                product_links.add(href)
                commercial_ref_tokens.add(p_match[1])

    # Category link discovery with priority filtering
    category_links = []
    breadcrumbs = []
    seen_cat_urls = set()

    # Priority 1: Breadcrumbs
    for a in page.query_selector_all("nav[aria-label*='Breadcrumb' i] a, nav[aria-label*='breadcrumbs' i] a, .breadcrumbs a"):
        href = a.get_attribute("href") or ""
        name = a.inner_text().strip()
        if category_route(href) and href not in seen_cat_urls:
            breadcrumbs.append({"url": href, "name": name, "context": "Breadcrumbs Trail"})
            category_links.append({"url": href, "name": name, "context": "Breadcrumbs Trail", "in_main": False})
            seen_cat_urls.add(href)

    # Priority 2: Local subcategories / related categories carousel
    for a in page.query_selector_all("nav[aria-label*='related categories' i] a, nav[class*='subcategories' i] a, [class*='category-list' i] a"):
        href = a.get_attribute("href") or ""
        name = a.inner_text().strip()
        if category_route(href) and href not in seen_cat_urls:
            category_links.append({"url": href, "name": name, "context": "Local Subcategories", "in_main": True})
            seen_cat_urls.add(href)

    # Priority 3: Related collection links inside main (excluding global header & footer)
    for a in page.query_selector_all("main a[href]"):
        try:
            is_excluded = a.evaluate("el => !!el.closest('header, footer, nav[aria-label*=\"Breadcrumb\" i], [class*=\"footer\" i]')")
            if is_excluded:
                continue
            href = a.get_attribute("href") or ""
            name = a.inner_text().strip()
            if category_route(href) and href not in seen_cat_urls:
                category_links.append({"url": href, "name": name, "context": "Main Content Related", "in_main": True})
                seen_cat_urls.add(href)
        except Exception:
            pass

    return {
        "final_url": final_url,
        "canonical": canonical,
        "page_title": page_title,
        "headings": headings,
        "main_heading": main_heading,
        "jsonld": jsonld_raw,
        "jsonld_types": jsonld_types,
        "visible_grid_products": card_count,
        "catalogue_product_ids": sorted(list(catalogue_product_ids)),
        "commercial_ref_tokens": sorted(list(commercial_ref_tokens)),
        "product_links": sorted(list(product_links)),
        "category_links": category_links,
        "breadcrumbs": breadcrumbs,
        "technical_restriction": restriction,
        "restriction_reason": restriction_reason
    }


def classify_category(evidence, previous_route_type=None):
    if evidence.get("technical_restriction"):
        return "TECHNICAL_RESTRICTION", f"Technical restriction: {evidence.get('restriction_reason')}"

    cards = evidence.get("visible_grid_products", 0)
    p_ids = len(evidence.get("catalogue_product_ids", []))
    p_links = len(evidence.get("product_links", []))
    jsonld_types = evidence.get("jsonld_types", [])

    # Direct evidence of product listing
    if cards > 0 or p_ids > 0 or p_links > 0 or "ItemList" in jsonld_types:
        return "PRODUCT_LISTING_CATEGORY", f"Observed product grid: {cards} visible cards, {p_ids} catalogue IDs, {p_links} product links, JSON-LD types {jsonld_types}"

    # Preserve known product listing from pilot (Constraint 6)
    if previous_route_type == "PRODUCT_LISTING_CATEGORY":
        return "PRODUCT_LISTING_CATEGORY", "Preserved established pilot product listing classification"

    # Collection or campaign page
    if "CollectionPage" in jsonld_types:
        return "COLLECTION_CAMPAIGN", "JSON-LD declared CollectionPage without product grid"

    # Navigation hub
    cat_links = len(evidence.get("category_links", []))
    if cat_links > 0:
        return "NAVIGATION_PAGE", f"Navigation hub: {cat_links} category links, zero product cards observed"

    return "UNKNOWN", "Insufficient evidence to determine route type"


def run_batch(batch_size=5):
    DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)
    
    # Read current state
    discovery_queue = read(STATE / 'category_discovery_queue.json', [])
    graph = read(STATE / 'category_graph.json', {"nodes": [], "edges": []})
    existing_nodes_by_id = {n['category_id']: n for n in graph.get('nodes', [])}
    existing_urls = {n['url'] for n in graph.get('nodes', [])}
    for q in discovery_queue:
        existing_urls.add(q['url'])

    # Pick batch items
    queued_items = [q for q in discovery_queue if q['status'] == 'QUEUED']
    batch = queued_items[:batch_size]

    if not batch:
        print("No pending items in category discovery queue.")
        return [], []

    print(f"\n==================================================")
    print(f"STARTING PHASE 1A BATCH: {len(batch)} items (Requested batch size: {batch_size})")
    print(f"Total pending before batch: {len(queued_items)}")
    print(f"==================================================\n")

    batch_results = []
    all_new_links = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=EDGE_PATH,
            headless=False
        )
        context = browser.new_context()

        for idx, item in enumerate(batch, 1):
            url = item['url']
            cat_id = item['id']
            dept = department(url)
            prev_node = existing_nodes_by_id.get(cat_id, {})
            prev_route_type = prev_node.get('route_type', 'UNKNOWN')

            print(f"[{idx}/{len(batch)}] Processing {cat_id} | {dept} | {url}")
            page = context.new_page()

            now_iso = datetime.now(timezone.utc).isoformat()
            error_state = None
            evidence = {}
            route_type = "UNKNOWN"
            reason = ""

            try:
                evidence = extract_page_evidence(page, url)
                route_type, reason = classify_category(evidence, prev_route_type)
            except Exception as e:
                error_state = str(e)
                route_type = "ERROR"
                reason = f"Extraction error: {error_state}"
                print(f"   ERROR: {error_state}")
            finally:
                page.close()

            print(f"   -> Result: {route_type} ({reason})")

            # Derive file token
            token_match = re.search(r'-(?:l|mkt|c)(\d+)\.html', url)
            if token_match:
                token = token_match[1]
            else:
                token = hashlib.sha256(url.encode()).hexdigest()[:16]

            evidence_file = DISCOVERY_DIR / f"{token}.json"

            # Check for newly discovered category links
            new_discovered = []
            for link in evidence.get("category_links", []):
                canon_link = canonicalize(link['url'])
                if canon_link not in existing_urls:
                    new_discovered.append(canon_link)
                    existing_urls.add(canon_link)
                    all_new_links.append(canon_link)

            # Build raw discovery document
            raw_doc = {
                "captured_at": now_iso,
                "url": url,
                "final_url": evidence.get("final_url", url),
                "canonical": evidence.get("canonical"),
                "department": dept,
                "title": evidence.get("page_title"),
                "headings": evidence.get("headings", []),
                "main_heading": evidence.get("main_heading"),
                "jsonld_types": evidence.get("jsonld_types", []),
                "visible_grid_products": evidence.get("visible_grid_products", 0),
                "product_card_count": evidence.get("visible_grid_products", 0),
                "catalogue_product_ids_count": len(evidence.get("catalogue_product_ids", [])),
                "commercial_ref_tokens_count": len(evidence.get("commercial_ref_tokens", [])),
                "product_links_count": len(evidence.get("product_links", [])),
                "catalogue_product_ids_sample": evidence.get("catalogue_product_ids", [])[:10],
                "commercial_ref_tokens_sample": evidence.get("commercial_ref_tokens", [])[:10],
                "links": evidence.get("category_links", []),
                "breadcrumbs": evidence.get("breadcrumbs", []),
                "technical_restriction": evidence.get("technical_restriction", False),
                "restriction_reason": evidence.get("restriction_reason"),
                "error": error_state,
                "route_type": route_type,
                "is_product_listing": route_type == "PRODUCT_LISTING_CATEGORY",
                "is_navigation_only": route_type == "NAVIGATION_PAGE",
                "is_collection_page": route_type == "COLLECTION_CAMPAIGN",
                "is_campaign_page": False,
                "classification_reason": reason,
                "discovery_complete": route_type not in ["TECHNICAL_RESTRICTION", "ERROR"]
            }

            write(evidence_file, raw_doc)

            # Update discovery queue item
            item['attempt_count'] = item.get('attempt_count', 0) + 1
            item['last_attempt_at'] = now_iso
            item['error'] = error_state
            item['status'] = "COMPLETE" if raw_doc["discovery_complete"] else ("TECHNICAL_RESTRICTION" if raw_doc["technical_restriction"] else "ERROR")
            item['checkpoint'] = {
                "evidence": str(evidence_file.relative_to(ROOT)),
                "phase": "classification",
                "enumeration_complete": False,
                "classification": route_type
            }

            batch_results.append({
                "category_id": cat_id,
                "url": url,
                "department": dept,
                "previous_route_type": prev_route_type,
                "observed_evidence": {
                    "title": evidence.get("page_title"),
                    "main_heading": evidence.get("main_heading"),
                    "visible_grid_products": evidence.get("visible_grid_products", 0),
                    "catalogue_product_ids": len(evidence.get("catalogue_product_ids", [])),
                    "commercial_ref_tokens": len(evidence.get("commercial_ref_tokens", [])),
                    "product_links": len(evidence.get("product_links", [])),
                    "jsonld_types": evidence.get("jsonld_types", []),
                    "category_links": len(evidence.get("category_links", [])),
                    "breadcrumbs": len(evidence.get("breadcrumbs", []))
                },
                "final_classification": route_type,
                "completion_status": item['status'],
                "newly_discovered_links": len(new_discovered),
                "new_links": new_discovered,
                "error_or_restriction": error_state or evidence.get("restriction_reason")
            })

        browser.close()

    # Save discovery queue atomically
    write(STATE / 'category_discovery_queue.json', discovery_queue)

    print("\nBatch extraction complete. Rebuilding graph and regenerating coverage...")
    repair_graph_build()

    return batch_results, all_new_links


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Classify category batch")
    parser.add_argument("--batch-size", type=int, default=5, help="Batch size to classify")
    args = parser.parse_args()

    results, new_links = run_batch(args.batch_size)
    print(f"\nCompleted {len(results)} items.")
    print(f"Newly discovered URLs: {len(new_links)}")
