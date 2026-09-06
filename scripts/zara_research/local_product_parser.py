"""Layer 3: Local Product Parser for Zara US.

Extracts structured data (JSON-LD ProductGroups) and DOM signals from
captured HTML source locally using BeautifulSoup and Python's json parser.
Zero browser IPC / DOM round-trips occur in this layer.
"""

import json
import re
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional


def parse_price(price_val: Any) -> Optional[str]:
    """Parse numeric price string into standardized format (e.g. '69.90')."""
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


def parse_product_group_jsonld(data: Any) -> Optional[Dict[str, Any]]:
    """Extract structured ProductGroup or Product entity from parsed JSON-LD."""
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
        brand = data.get("brand")

    description = data.get("description", "").strip() or None
    material = data.get("material", "").strip() or None

    composition = None
    if "additionalProperty" in data and isinstance(data["additionalProperty"], list):
        comp_parts = []
        for prop in data["additionalProperty"]:
            if isinstance(prop, dict):
                p_name = prop.get("name", "")
                p_val = prop.get("value", "")
                if p_name and p_val:
                    comp_parts.append(f"{p_name}: {p_val}")
        if comp_parts:
            composition = " | ".join(comp_parts)

    offers = data.get("offers", {})
    price = None
    currency = "USD"
    if isinstance(offers, dict):
        price = parse_price(offers.get("price"))
        currency = offers.get("priceCurrency", "USD")
    elif isinstance(offers, list) and offers:
        first_offer = offers[0]
        if isinstance(first_offer, dict):
            price = parse_price(first_offer.get("price"))
            currency = first_offer.get("priceCurrency", "USD")

    variants = []
    has_variant = data.get("hasVariant", [])
    if isinstance(has_variant, dict):
        has_variant = [has_variant]

    for v in has_variant:
        if not isinstance(v, dict):
            continue
        v_name = v.get("name")
        sku = v.get("sku")
        mpn = v.get("mpn")
        color = v.get("color")
        size = v.get("size")
        v_offers = v.get("offers", {})
        v_price = price
        v_avail = "UNKNOWN"
        v_url = None
        if isinstance(v_offers, dict):
            v_price = parse_price(v_offers.get("price")) or price
            avail_str = v_offers.get("availability", "")
            if "InStock" in avail_str:
                v_avail = "IN_STOCK"
            elif "OutOfStock" in avail_str:
                v_avail = "OUT_OF_STOCK"
            v_url = v_offers.get("url")

        v_images = []
        if "image" in v:
            imgs = v["image"]
            if isinstance(imgs, str):
                imgs = [imgs]
            if isinstance(imgs, list):
                for img_url in imgs:
                    if isinstance(img_url, str):
                        v_images.append(img_url)

        variants.append({
            "name": v_name,
            "sku": sku,
            "mpn": mpn,
            "color_name": color,
            "size_name": size,
            "price": v_price,
            "public_availability_state": v_avail,
            "offer_url": v_url,
            "images": v_images
        })

    images = []
    if "image" in data:
        img_data = data["image"]
        if isinstance(img_data, str):
            img_data = [img_data]
        if isinstance(img_data, list):
            for item in img_data:
                if isinstance(item, str):
                    images.append(item)
                elif isinstance(item, dict) and "contentUrl" in item:
                    images.append(item["contentUrl"])

    return {
        "name": name,
        "product_group_id": product_group_id,
        "brand": brand,
        "description": description,
        "material": material,
        "composition": composition,
        "price": price,
        "currency": currency,
        "offers": offers,
        "variants": variants,
        "images": images
    }


def parse_page_evidence_locally(source_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Parse captured HTML source bundle locally using BeautifulSoup and JSON parser.
    
    Args:
        source_bundle: Dict containing:
            - html: Rendered page HTML string
            - final_url: URL after any redirects
            - http_status: HTTP status code
            - page_title: Page title string
            
    Returns:
        evidence: Standardized evidence dictionary compatible with build_normalized_records
    """
    html_content = source_bundle.get("html", "")
    final_url = source_bundle.get("final_url")
    http_status = source_bundle.get("http_status")
    page_title = (source_bundle.get("page_title") or "").strip()

    soup = BeautifulSoup(html_content, "html.parser")

    # Canonical link
    canonical_url = None
    canon_el = soup.find("link", rel=lambda val: val and "canonical" in val.lower())
    if canon_el and canon_el.get("href"):
        canonical_url = canon_el["href"].strip()

    # JSON-LD Structured Data
    jsonld_raw = []
    parsed_product_groups = []
    for s in soup.find_all("script", type="application/ld+json"):
        text = s.string or s.get_text() or ""
        text = text.strip()
        if not text:
            continue
        try:
            data = json.loads(text)
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

    # Scope DOM extraction to the primary product view to avoid recommendation carousels
    primary_scope = soup.select_one("main, .product-detail-view, .product-detail-info, [data-qa-qualifier='product-detail']") or soup

    # Rendered Headings
    headings = []
    for h in primary_scope.find_all(["h1", "h2"]):
        txt = h.get_text(strip=True)
        if txt and txt not in headings:
            headings.append(txt)
    main_heading = headings[0] if headings else None

    # Full text representation of primary container
    body_text = primary_scope.get_text(separator=" ", strip=True) if primary_scope else ""

    # Check for security challenge / restriction
    restriction = False
    restriction_reason = None
    if "Access Denied" in page_title or "access denied" in page_title.lower():
        restriction = True
        restriction_reason = "Access Denied in title"
    elif any(k in body_text.lower() for k in ["verify you are human", "security check", "cf-turnstile"]):
        restriction = True
        restriction_reason = "Verification challenge detected"

    # Rendered Prices from DOM (scoped to primary product info)
    rendered_price = None
    rendered_old_price = None
    rendered_sale_price = None

    price_scope = primary_scope.select_one(".product-detail-info, .price, .product-detail-view") or primary_scope

    old_price_el = price_scope.select_one(".price-old__amount, .money-amount__old, .price__amount--old")
    if old_price_el:
        rendered_old_price = parse_price(old_price_el.get_text())

    sale_price_el = price_scope.select_one(".price-sale__amount, .money-amount__sale, .price__amount--sale")
    if sale_price_el:
        rendered_sale_price = parse_price(sale_price_el.get_text())

    price_el = price_scope.select_one(".price-current__amount, .money-amount__main, .price__amount")
    if price_el:
        rendered_price = parse_price(price_el.get_text())

    if not rendered_price:
        match = re.search(r'\$\s*([\d,]+\.\d{2})', body_text)
        if match:
            rendered_price = parse_price(match.group(1))

    # Commercial reference from text
    commercial_ref = None
    match_ref = re.search(r'(\d{4}/\d{3}/\d{3})', body_text)
    if match_ref:
        commercial_ref = match_ref.group(1)

    # Rendered Description
    rendered_desc = None
    desc_el = primary_scope.select_one(".product-detail-description, .product-description, [data-qa-qualifier='product-description']")
    if desc_el:
        rendered_desc = desc_el.get_text(separator="\n", strip=True)

    # Composition & Care
    comp_care_text = None
    care_el = primary_scope.select_one(".product-detail-extra-detail, .product-detail-composition-and-care, [data-qa-qualifier='product-composition-and-care']")
    if care_el:
        comp_care_text = care_el.get_text(separator="\n", strip=True)

    # Color choices from DOM buttons
    dom_colors = []
    color_buttons = primary_scope.select("button.product-detail-color-item__color-button, .product-detail-color-selector button, .color-selector button")
    for btn in color_buttons:
        btn_classes = " ".join(btn.get("class", []))
        if any(bad in btn_classes for bad in ["copy-action", "reference", "share", "size-guide", "action"]):
            continue
        txt = btn.get_text(strip=True)
        aria = btn.get("aria-label", "").strip()
        label = txt or aria
        if label and label not in dom_colors and "\n" not in label and not re.match(r'^\d{4}/\d{3}/\d{3}$', label):
            dom_colors.append(label)

    # Rendered Images from DOM (inside main product viewer)
    raw_images = []
    for img in primary_scope.select(".product-detail-images img, .media-carousel img, main img"):
        # Ignore images inside recommendation carousels
        parent_classes = " ".join(getattr(img.parent, "get", lambda k, d="": d)("class", []))
        if "recommendation" in parent_classes or "similar" in parent_classes:
            continue
        src = img.get("src", "").strip()
        srcset = img.get("srcset", "").strip()
        data_src = img.get("data-src", "").strip()
        alt = img.get("alt", "").strip()
        best_url = None
        if srcset:
            parts = [p.strip().split(" ") for p in srcset.split(",") if p.strip()]
            if parts:
                best_url = parts[-1][0]
        if not best_url:
            best_url = data_src or src

        if best_url:
            raw_images.append({"url": best_url, "alt": alt, "is_structured": False})

    return {
        "final_url": final_url,
        "canonical_url": canonical_url,
        "http_status": http_status,
        "page_title": page_title,
        "headings": headings,
        "main_heading": main_heading,
        "rendered_price": rendered_price,
        "rendered_old_price": rendered_old_price,
        "rendered_sale_price": rendered_sale_price,
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


def parse_page_source_from_disk(html_path: Path, meta_path: Optional[Path] = None) -> Dict[str, Any]:
    """Parse HTML and metadata directly from disk without any browser connection.
    
    Args:
        html_path: Path to captured .html file
        meta_path: Optional path to captured .meta.json file
        
    Returns:
        evidence: Standardized evidence dictionary compatible with build_normalized_records
    """
    html_content = html_path.read_text(encoding="utf-8")
    meta = {}
    if meta_path and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    source_bundle = {
        "html": html_content,
        "final_url": meta.get("final_url"),
        "http_status": meta.get("http_status", 200),
        "page_title": meta.get("page_title", "")
    }
    return parse_page_evidence_locally(source_bundle)


def batch_parse_sources_from_dir(source_dir: Path) -> List[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
    """Offline batch parse all captured source files in a directory.
    
    Returns list of (product_id, evidence, meta) tuples.
    """
    results = []
    for html_file in sorted(source_dir.glob("*.html")):
        clean_id = html_file.stem
        meta_file = source_dir / f"{clean_id}.meta.json"
        meta = {}
        if meta_file.exists():
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        product_id = meta.get("product_id") or clean_id.replace("_", ":", 1)
        evidence = parse_page_source_from_disk(html_file, meta_file)
        results.append((product_id, evidence, meta))
    return results
