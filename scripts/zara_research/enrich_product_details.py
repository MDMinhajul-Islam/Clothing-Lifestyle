"""Phase 1C Product Detail Enrichment Engine.

Enriches queued products with exact public product-page data from Zara US.
Extracts identity, content, pricing, explicit non-Cartesian variants, colors,
and high-resolution image provenance from ProductGroup JSON-LD and rendered DOM.
Persists atomically and maintains resumable checkpoints.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/zara_research'))
from catalogue_progress import RAW, STATE, read, write

PRODUCT_DETAILS_RAW = RAW / 'product_details'
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PARSER_VERSION = "phase_1c_v1.0"


def clean_url(url):
    if not url:
        return None
    p = urlsplit(url)
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, p.query, ''))


def parse_price(price_val):
    if price_val is None:
        return None
    if isinstance(price_val, (int, float)):
        return f"{price_val:.2f}"
    cleaned = re.sub(r'[^\d.]', '', str(price_val).strip())
    try:
        val = float(cleaned)
        return f"{val:.2f}"
    except ValueError:
        return None


def parse_product_group_jsonld(data):
    if not isinstance(data, dict):
        return None
    if data.get("@type") not in ["ProductGroup", "Product"]:
        return None

    name = data.get("name", "").strip() or None
    product_group_id = data.get("productGroupID")
    brand = "ZARA"
    if isinstance(data.get("brand"), dict):
        brand = data["brand"].get("name", "ZARA")
    elif isinstance(data.get("brand"), str):
        brand = data["brand"]

    description = data.get("description", "").strip() or None
    material = data.get("material", "").strip() or None

    # Composition from additionalProperty
    composition_parts = []
    for prop in data.get("additionalProperty", []):
        if isinstance(prop, dict):
            prop_name = prop.get("name") or prop.get("propertyID") or ""
            val = prop.get("value") or ""
            if prop_name and val:
                composition_parts.append(f"{prop_name.strip()}: {val.strip()}")
    composition = "; ".join(composition_parts) if composition_parts else None

    # High-level images
    images = []
    raw_imgs = data.get("image", [])
    if isinstance(raw_imgs, str):
        raw_imgs = [raw_imgs]
    for img in raw_imgs:
        if isinstance(img, str) and img.strip():
            images.append(img.strip())

    # Variants from hasVariant
    variants = []
    raw_variants = data.get("hasVariant", [])
    if isinstance(raw_variants, dict):
        raw_variants = [raw_variants]

    for var in raw_variants:
        if not isinstance(var, dict):
            continue
        v_name = var.get("name", "")
        v_sku = var.get("sku") or var.get("mpn")
        v_color = var.get("color")
        v_size = var.get("size")
        v_images = []
        v_raw_imgs = var.get("image", [])
        if isinstance(v_raw_imgs, str):
            v_raw_imgs = [v_raw_imgs]
        for img in v_raw_imgs:
            if isinstance(img, str) and img.strip():
                v_images.append(img.strip())

        offers = var.get("offers", {})
        price = None
        currency = "USD"
        avail_state = "UNKNOWN"
        v_url = None

        if isinstance(offers, dict):
            currency = offers.get("priceCurrency", "USD")
            price = parse_price(offers.get("price"))
            v_url = offers.get("url")
            raw_avail = offers.get("availability", "")
            if "InStock" in raw_avail:
                avail_state = "IN_STOCK"
            elif "OutOfStock" in raw_avail:
                avail_state = "OUT_OF_STOCK"
            elif "PreOrder" in raw_avail:
                avail_state = "COMING_SOON"

        variants.append({
            "name": v_name,
            "sku": v_sku,
            "mpn": var.get("mpn"),
            "color_name": v_color,
            "size_name": v_size,
            "price": price,
            "currency": currency,
            "public_availability_state": avail_state,
            "variant_url": v_url,
            "images": v_images
        })

    return {
        "name": name,
        "product_group_id": product_group_id,
        "brand": brand,
        "description": description,
        "material": material,
        "composition": composition,
        "images": images,
        "variants": variants
    }


def filter_valid_product_images(raw_images, product_group_id=None):
    valid = []
    seen_urls = set()

    for item in raw_images:
        url = item.get("url", "").strip() if isinstance(item, dict) else str(item).strip()
        alt = item.get("alt", "").strip() if isinstance(item, dict) else ""
        if not url:
            continue

        # Reject placeholder, tracking, logo, and svg assets
        url_lower = url.lower()
        if any(bad in url_lower for bad in [
            "transparent-background", "placeholder", "pixel.gif", "tracking",
            "logo.svg", "icon", "spinner", "blank.gif", "favicon"
        ]):
            continue

        # Must be from static.zara.net or look like a product image
        if "static.zara.net" not in url_lower and not re.search(r'\.(?:jpg|jpeg|png|webp)', url_lower):
            continue

        # Normalize to maximum resolution where feasible
        clean_img_url = url
        if "w=" in clean_img_url:
            clean_img_url = re.sub(r'w=\d+', 'w=1920', clean_img_url)

        if clean_img_url not in seen_urls:
            seen_urls.add(clean_img_url)
            # Infer role
            role = "GALLERY"
            if len(valid) == 0:
                role = "PRIMARY"
            elif any(k in clean_img_url.lower() for k in ["-e1", "-e2", "-detail"]):
                role = "DETAIL"
            elif any(k in clean_img_url.lower() for k in ["-a", "-b"]):
                role = "GALLERY"

            valid.append({
                "url": clean_img_url,
                "alt": alt,
                "inferred_role": role
            })

    return valid


def compute_content_hash(product_record, colors, variants, images):
    stable_dict = {
        "exact_product_name": product_record.get("exact_product_name"),
        "currency": product_record.get("currency"),
        "current_price": product_record.get("current_price"),
        "original_price": product_record.get("original_price"),
        "sale_price": product_record.get("sale_price"),
        "is_on_sale": product_record.get("is_on_sale"),
        "material_text": product_record.get("material_text"),
        "composition_text": product_record.get("composition_text"),
        "colors": sorted([c.get("color_name") or "" for c in colors]),
        "variants": sorted([
            f"{v.get('color_name')}:{v.get('size_name')}:{v.get('sku')}:{v.get('public_availability_state')}"
            for v in variants
        ]),
        "images": [img.get("source_image_url") for img in sorted(images, key=lambda x: x.get("display_order", 0))]
    }
    encoded = json.dumps(stable_dict, sort_keys=True).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def extract_page_evidence(page, url):
    response = page.goto(url, timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(3500)

    # Dismiss cookie banner
    try:
        accept_btn = page.query_selector("#onetrust-accept-btn-handler, button#onetrust-accept-btn-handler")
        if accept_btn and accept_btn.is_visible():
            accept_btn.click()
            page.wait_for_timeout(1000)
    except Exception:
        pass

    final_url = page.url
    http_status = response.status if response else None

    # Check for security challenge
    page_title = page.title().strip()
    body_text = ""
    try:
        body_text = page.inner_text("body")[:4000]
    except Exception:
        pass

    restriction = False
    restriction_reason = None
    if "Access Denied" in page_title or "access denied" in page_title.lower():
        restriction = True
        restriction_reason = "Access Denied in title"
    elif any(k in body_text.lower() for k in ["verify you are human", "security check", "cf-turnstile"]):
        restriction = True
        restriction_reason = "Verification challenge detected"

    # Canonical link
    canonical_url = None
    try:
        canon_el = page.query_selector('link[rel="canonical"]')
        if canon_el:
            canonical_url = canon_el.get_attribute("href")
    except Exception:
        pass

    # JSON-LD Structured Data
    jsonld_raw = []
    parsed_product_groups = []
    for s in page.query_selector_all('script[type="application/ld+json"]'):
        try:
            content = s.inner_text()
            data = json.loads(content)
            jsonld_raw.append(data)
            if isinstance(data, dict):
                pg = parse_product_group_jsonld(data)
                if pg:
                    parsed_product_groups.append(pg)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        pg = parse_product_group_jsonld(item)
                        if pg:
                            parsed_product_groups.append(pg)
        except Exception:
            pass

    # Rendered DOM Headings
    headings = []
    for h in page.query_selector_all("h1, h2"):
        txt = h.inner_text().strip()
        if txt and txt not in headings:
            headings.append(txt)
    main_heading = headings[0] if headings else None

    # Rendered Price from DOM
    rendered_price = None
    try:
        price_el = page.query_selector(".price-current__amount, .money-amount__main, .price__amount")
        if price_el:
            rendered_price = parse_price(price_el.inner_text())
        if not rendered_price:
            match = re.search(r'\$\s*([\d,]+\.\d{2})', body_text)
            if match:
                rendered_price = parse_price(match.group(1))
    except Exception:
        pass

    # Commercial reference from DOM text (e.g. 0122/342/412)
    commercial_ref = None
    match_ref = re.search(r'(\d{4}/\d{3}/\d{3})', body_text)
    if match_ref:
        commercial_ref = match_ref.group(1)

    # Rendered Description
    rendered_desc = None
    try:
        desc_el = page.query_selector(".product-detail-description, .product-description, [data-qa-qualifier='product-description']")
        if desc_el:
            rendered_desc = desc_el.inner_text().strip()
    except Exception:
        pass

    # Composition & Care from DOM
    comp_care_text = None
    try:
        care_el = page.query_selector(".product-detail-extra-detail, .product-detail-composition-and-care, [data-qa-qualifier='product-composition-and-care']")
        if care_el:
            comp_care_text = care_el.inner_text().strip()
    except Exception:
        pass

    # Color choices from DOM
    dom_colors = []
    for btn in page.query_selector_all(".product-detail-color-selector button, .color-selector button, [class*='color-selector']"):
        txt = btn.inner_text().strip()
        aria = btn.get_attribute("aria-label") or ""
        label = txt or aria
        if label and label not in dom_colors:
            dom_colors.append(label)

    # Rendered Images from DOM
    raw_images = []
    for img in page.query_selector_all("img"):
        src = img.get_attribute("src") or ""
        srcset = img.get_attribute("srcset") or ""
        data_src = img.get_attribute("data-src") or ""
        alt = img.get_attribute("alt") or ""
        best_url = None
        if srcset:
            parts = [p.strip().split(" ") for p in srcset.split(",") if p.strip()]
            if parts:
                best_url = parts[-1][0]
        if not best_url:
            best_url = data_src or src

        if best_url:
            raw_images.append({"url": best_url, "alt": alt})

    return {
        "final_url": final_url,
        "canonical_url": canonical_url,
        "http_status": http_status,
        "page_title": page_title,
        "headings": headings,
        "main_heading": main_heading,
        "rendered_price": rendered_price,
        "commercial_ref": commercial_ref,
        "rendered_description": rendered_desc,
        "comp_care_text": comp_care_text,
        "dom_colors": dom_colors,
        "jsonld_raw": jsonld_raw,
        "parsed_product_groups": parsed_product_groups,
        "raw_images": raw_images,
        "body_text_sample": body_text[:1000],
        "restriction": restriction,
        "restriction_reason": restriction_reason
    }


def build_normalized_records(evidence, global_product, now_iso):
    pid = global_product["product_id"]
    source_pid = global_product.get("source_product_id")
    url = global_product.get("product_url")
    first_seen_at = global_product.get("first_seen_at", now_iso)
    first_cat = global_product.get("first_seen_category", "")

    # Department derivation
    department = "WOMAN"
    if "/woman-beauty-" in first_cat or "beauty" in first_cat:
        department = "BEAUTY"
    elif "/home-" in first_cat:
        department = "ZARA HOME"
    elif "/kids-" in first_cat:
        department = "KIDS"
    elif "/man-" in first_cat:
        department = "MAN"

    # Prioritize JSON-LD ProductGroup
    pg = evidence["parsed_product_groups"][0] if evidence.get("parsed_product_groups") else {}

    exact_name = pg.get("name") or evidence.get("main_heading") or global_product.get("name") or "Zara Product"
    product_group_id = pg.get("product_group_id") or source_pid
    brand = pg.get("brand") or ("ZARA HOME" if department == "ZARA HOME" else "ZARA")
    description = pg.get("description") or evidence.get("rendered_description")
    material_text = pg.get("material")
    composition_text = pg.get("composition") or evidence.get("comp_care_text")

    # Commercial reference
    comm_ref = evidence.get("commercial_ref")

    # Pricing resolution
    # 1. First variant price in JSON-LD
    variant_prices = [v["price"] for v in pg.get("variants", []) if v.get("price")]
    price = variant_prices[0] if variant_prices else evidence.get("rendered_price")
    currency = "USD"
    if pg.get("variants") and pg["variants"][0].get("currency"):
        currency = pg["variants"][0]["currency"]

    is_on_sale = False
    original_price = None
    sale_price = None

    # Variants extraction (Strict Non-Cartesian)
    variant_records = []
    observed_colors = set()

    for idx, v in enumerate(pg.get("variants", [])):
        v_sku = v.get("sku") or f"{source_pid}-{idx+1}"
        v_color = v.get("color_name")
        v_size = v.get("size_name")
        v_avail = v.get("public_availability_state", "UNKNOWN")
        v_url = v.get("variant_url")

        if v_color:
            observed_colors.add(v_color)

        var_id = f"{pid}:{v_sku}"
        variant_records.append({
            "variant_id": var_id,
            "product_id": pid,
            "source_product_id": source_pid,
            "commercial_reference": comm_ref,
            "sku": v_sku,
            "color_name": v_color,
            "color_code": None,
            "size_name": v_size,
            "size_code": None,
            "size_label": v_size,
            "public_availability_state": v_avail,
            "variant_url": v_url,
            "first_seen_at": first_seen_at,
            "last_seen_at": now_iso
        })

    # If no structured variants, record single default variant if apparel/home
    if not variant_records and exact_name:
        variant_records.append({
            "variant_id": f"{pid}:default",
            "product_id": pid,
            "source_product_id": source_pid,
            "commercial_reference": comm_ref,
            "sku": source_pid,
            "color_name": None,
            "color_code": None,
            "size_name": "One Size",
            "size_code": None,
            "size_label": "One Size",
            "public_availability_state": "IN_STOCK",
            "variant_url": url,
            "first_seen_at": first_seen_at,
            "last_seen_at": now_iso
        })

    # Colors extraction
    color_records = []
    # Combine JSON-LD colors and DOM colors
    all_colors = list(observed_colors)
    for dc in evidence.get("dom_colors", []):
        if dc not in all_colors:
            all_colors.append(dc)

    for order_idx, cname in enumerate(all_colors):
        color_slug = re.sub(r'[^\w]+', '-', cname.lower()).strip('-')
        color_id = f"{pid}:{color_slug}"
        color_records.append({
            "color_id": color_id,
            "product_id": pid,
            "color_name": cname,
            "color_code": None,
            "color_reference": comm_ref,
            "color_specific_url": None,
            "display_order": order_idx,
            "last_verified_at": now_iso
        })

    # Images extraction & quality filtering
    candidate_images = []
    # Include JSON-LD images first (they are pristine high-res)
    for img_url in pg.get("images", []):
        candidate_images.append({"url": img_url, "alt": exact_name})
    # Include DOM images
    for d_img in evidence.get("raw_images", []):
        candidate_images.append(d_img)

    valid_images = filter_valid_product_images(candidate_images, product_group_id=source_pid)
    image_records = []
    for img_idx, v_img in enumerate(valid_images):
        img_url = v_img["url"]
        img_id = hashlib.sha256(f"{pid}:{img_url}".encode()).hexdigest()[:16]

        # Associate color if color name appears in alt text
        img_color = None
        for c in all_colors:
            if c.lower() in v_img.get("alt", "").lower():
                img_color = c
                break

        image_records.append({
            "image_id": f"img-{img_id}",
            "product_id": pid,
            "variant_id": None,
            "color_name": img_color,
            "color_code": None,
            "source_image_url": img_url,
            "image_role": v_img.get("inferred_role", "GALLERY"),
            "display_order": img_idx,
            "alt_text": v_img.get("alt") or exact_name,
            "image_last_verified_at": now_iso
        })

    # Master product record
    product_record = {
        "product_id": pid,
        "source_product_id": source_pid,
        "product_group_id": product_group_id,
        "commercial_reference": comm_ref,
        "sku": variant_records[0]["sku"] if variant_records else source_pid,
        "product_url": url,
        "canonical_url": evidence.get("canonical_url") or url,
        "department": department,
        "brand": brand,
        "market": "US",
        "locale": "en",
        "exact_product_name": exact_name,
        "short_description": description[:120] + "..." if description and len(description) > 120 else description,
        "long_description": description,
        "fit_information": None,
        "care_information": None,
        "composition_text": composition_text,
        "material_text": material_text,
        "currency": currency,
        "current_price": price,
        "original_price": original_price,
        "sale_price": sale_price,
        "is_on_sale": is_on_sale,
        "price_last_verified_at": now_iso,
        "first_seen_at": first_seen_at,
        "last_seen_at": now_iso,
        "last_synced_at": now_iso,
        "source_content_hash": None,
        "lifecycle_status": "ACTIVE",
        "enrichment_status": "COMPLETE" if price and exact_name else "PARTIAL"
    }

    # Compute deterministic content hash
    content_hash = compute_content_hash(product_record, color_records, variant_records, image_records)
    product_record["source_content_hash"] = content_hash

    return product_record, variant_records, color_records, image_records


def run_enrichment_batch(product_ids=None, batch_size=20):
    PRODUCT_DETAILS_RAW.mkdir(parents=True, exist_ok=True)

    # Read state
    product_queue = read(STATE / 'product_detail_queue.json', [])
    unique_products = read(STATE / 'unique_products.json', [])
    unique_map = {p["product_id"]: p for p in unique_products}

    # Read existing normalized datasets if present
    normalized_products = read(STATE / 'product_details.json', [])
    normalized_variants = read(STATE / 'product_variants.json', [])
    normalized_colors = read(STATE / 'product_colors.json', [])
    normalized_images = read(STATE / 'product_images.json', [])

    existing_prod_map = {p["product_id"]: p for p in normalized_products}
    existing_var_map = {v["variant_id"]: v for v in normalized_variants}
    existing_col_map = {c["color_id"]: c for c in normalized_colors}
    existing_img_map = {img["image_id"]: img for img in normalized_images}

    # Determine batch items
    queue_by_id = {q["id"]: q for q in product_queue}
    batch_items = []

    if product_ids:
        for pid in product_ids:
            if pid in queue_by_id:
                batch_items.append(queue_by_id[pid])
            else:
                print(f"Warning: requested product ID {pid} not found in detail queue.")
    else:
        pending = [q for q in product_queue if q.get("status") in ["QUEUED", "PARTIAL", "FAILED_RETRYABLE"]]
        batch_items = pending[:batch_size]

    if not batch_items:
        print("No pending products to enrich.")
        return [], {}

    print(f"\n==================================================")
    print(f"STARTING PHASE 1C ENRICHMENT: {len(batch_items)} products")
    print(f"==================================================\n")

    results_summary = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=EDGE_PATH,
            headless=False
        )
        context = browser.new_context()

        for idx, item in enumerate(batch_items, 1):
            pid = item["id"]
            url = item.get("url")
            global_p = unique_map.get(pid, {"product_id": pid, "product_url": url})
            source_pid = global_p.get("source_product_id") or pid.split(":")[-1]

            print(f"[{idx}/{len(batch_items)}] Enriching {pid} | {url}")

            if not url:
                print(f"   SKIP: Product has no direct URL.")
                item["status"] = "FAILED_TERMINAL"
                item["error"] = "Product has no public URL"
                continue

            now_iso = datetime.now(timezone.utc).isoformat()
            page = context.new_page()
            evidence = {}
            error_msg = None

            try:
                evidence = extract_page_evidence(page, url)
                if evidence.get("restriction"):
                    error_msg = f"Restriction encountered: {evidence.get('restriction_reason')}"
                    item["status"] = "FAILED_RETRYABLE"
                    item["error"] = error_msg
                    print(f"   RESTRICTION: {error_msg}")
                elif evidence.get("http_status") == 404:
                    error_msg = "HTTP 404 Not Found"
                    item["status"] = "FAILED_TERMINAL"
                    item["error"] = error_msg
                    print(f"   NOT FOUND: 404")
                else:
                    # Successfully extracted
                    prod_rec, vars_rec, cols_rec, imgs_rec = build_normalized_records(evidence, global_p, now_iso)

                    # Update master indexes
                    existing_prod_map[pid] = prod_rec
                    for v in vars_rec:
                        existing_var_map[v["variant_id"]] = v
                    for c in cols_rec:
                        existing_col_map[c["color_id"]] = c
                    for img in imgs_rec:
                        existing_img_map[img["image_id"]] = img

                    # Save raw evidence
                    raw_file = PRODUCT_DETAILS_RAW / f"{source_pid}.json"
                    raw_doc = {
                        "product_id": pid,
                        "source_product_id": source_pid,
                        "source_url": url,
                        "final_url": evidence.get("final_url"),
                        "canonical_url": evidence.get("canonical_url"),
                        "retrieved_at": now_iso,
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
                        "source_content_hash": prod_rec["source_content_hash"],
                        "parser_version": PARSER_VERSION
                    }
                    write(raw_file, raw_doc)

                    item["status"] = prod_rec["enrichment_status"]
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

                    results_summary.append({
                        "product_id": pid,
                        "department": prod_rec["department"],
                        "name": prod_rec["exact_product_name"],
                        "price": prod_rec["current_price"],
                        "variants": len(vars_rec),
                        "colors": len(cols_rec),
                        "images": len(imgs_rec),
                        "composition": bool(prod_rec["composition_text"]),
                        "status": item["status"]
                    })

                    print(f"   -> Enriched: '{prod_rec['exact_product_name']}' | Price: ${prod_rec['current_price']} | Variants: {len(vars_rec)} | Colors: {len(cols_rec)} | Images: {len(imgs_rec)} | Hash: {prod_rec['source_content_hash'][:8]}")

            except Exception as e:
                error_msg = str(e)
                item["status"] = "FAILED_RETRYABLE"
                item["attempt_count"] = item.get("attempt_count", 0) + 1
                item["last_attempt_at"] = now_iso
                item["error"] = error_msg
                print(f"   ERROR: {error_msg}")
            finally:
                page.close()

            # Atomically persist updated queues and normalized tables after each product
            write(STATE / 'product_detail_queue.json', product_queue)
            write(STATE / 'product_details.json', list(existing_prod_map.values()))
            write(STATE / 'product_variants.json', list(existing_var_map.values()))
            write(STATE / 'product_colors.json', list(existing_col_map.values()))
            write(STATE / 'product_images.json', list(existing_img_map.values()))

        browser.close()

    print(f"\nEnrichment batch completed. Processed {len(results_summary)} items.")
    return results_summary, {
        "total_attempted": len(batch_items),
        "total_completed": sum(1 for r in results_summary if r["status"] == "COMPLETE"),
        "total_partial": sum(1 for r in results_summary if r["status"] == "PARTIAL"),
        "total_failed": len(batch_items) - len(results_summary),
        "normalized_products_count": len(existing_prod_map),
        "normalized_variants_count": len(existing_var_map),
        "normalized_colors_count": len(existing_col_map),
        "normalized_images_count": len(existing_img_map)
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Phase 1C Product Detail Enrichment Worker")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size to enrich")
    parser.add_argument("--product-ids", type=str, default=None, help="Comma-separated product IDs to process")
    args = parser.parse_args()

    p_ids = [p.strip() for p in args.product_ids.split(",") if p.strip()] if args.product_ids else None
    results, metrics = run_enrichment_batch(product_ids=p_ids, batch_size=args.batch_size)
    print("\nBatch Metrics:")
    print(json.dumps(metrics, indent=2))

