# Zara Product Evidence Validation Report

**Phase**: 1A — Category Graph Classification Diagnostic  
**Date**: 2026-09-06  
**Scope**: In-depth diagnostic of product evidence sources on four processed category listing routes:
- `woman-dresses-party-l1581.html`
- `woman-dresses-midi-l1081.html`
- `woman-dresses-mini-l1083.html`
- `woman-jumpsuits-l1150.html`

---

## 1. Executive Summary: The 40 / 39 / 79 Discrepancy Resolved

During the pilot classification batch, four different category listing pages reported nearly identical counts:
- ~40 visible cards
- ~39 product detail links
- ~79 unique product IDs

### Root Cause Analysis
The observation of 79 IDs was an artifact of mixing two distinct identifier namespaces into a single Python set:
1. **Internal Catalogue Product IDs (`data-productid`)**:
   - Each rendered product card in Zara's DOM container carries a `data-productid` attribute (e.g., `545425987`, `545426194`), which is a 9-digit internal Inditex catalogue identifier.
   - On initial viewport load, Zara renders exactly **40 product cards**, yielding **40 distinct `data-productid` values**.
2. **Commercial SKU / Model Reference Tokens (`-p(\d+).html`)**:
   - The product detail links on those cards link to URLs matching `-p(\d+).html` (e.g., `/ruched-dress-p01067703.html`), where the 8-digit numeric token (`01067703`) is the commercial reference code.
   - Out of the 40 cards, **39 cards** contained rendered anchor links to product detail pages (1 card was an editorial placeholder/promo card), yielding **39 distinct commercial reference tokens**.
3. **The 79 Combined Count**:
   - The extractor in `classify_batch.py` added both the 9-digit internal `data-productid` values and the 8-digit URL regex matches into the same `product_ids` set.
   - Because the two namespaces share **zero overlap** (`overlap = 0`), the set union yielded:
     $$\text{40 (internal IDs)} + \text{39 (commercial reference tokens)} = \mathbf{79 \text{ unique values}}.$$
   - **Crucial finding**: The 79 IDs do **not** represent 79 distinct catalogue products. They represent 40 actual products identified through two parallel naming conventions.

---

## 2. Product Evidence Comparison by Source

| Category Route | `VISIBLE_GRID_PRODUCTS` | `GRID_PRODUCT_LINKS` | `ITEMLIST_PRODUCTS` | `ALL_DOM_PRODUCT_IDS` | Commercial SKU Tokens (`-p...`) | Combined Set (Classifier) |
|---|---:|---:|---:|---:|---:|---:|
| `woman-dresses-party-l1581.html` | 40 | 39 | 10 | 40 | 39 | 79 |
| `woman-dresses-midi-l1081.html` | 40 | 39 | 10 | 40 | 39 | 79 |
| `woman-dresses-mini-l1083.html` | 40 | 39 | 10 | 40 | 39 | 79 |
| `woman-jumpsuits-l1150.html` | 40 | 39 | 10 | 40 | 39 | 79 |

### Source Characteristics
- **`VISIBLE_GRID_PRODUCTS` (40)**:
  - Count of rendered product card elements (`.product-grid-product, li.product-grid-product`) inside the main product grid section. All 40 are visible on initial settled DOM load.
- **`GRID_PRODUCT_LINKS` (39)**:
  - Distinct product detail URLs (`-p\d+\.html`) contained directly within the product cards of the grid. 39 of the 40 cards carry direct navigation to individual product pages; 1 card is an unlinked lookbook / editorial card.
- **`ITEMLIST_PRODUCTS` (10)**:
  - Count of items declared in Zara's server-rendered `<script type="application/ld+json">` with `@type: "ItemList"`.
  - Zara restricts this structured data array to the first 10 items as a standardized SEO payload; it does not reflect the complete rendered viewport grid.
- **`ALL_DOM_PRODUCT_IDS` (40)**:
  - Distinct `data-productid` attributes across the entire page DOM. All 40 occur exclusively within the product grid cards; no hidden product IDs or background preloaded product lists exist elsewhere in the document.

---

## 3. Authoritative Listing Count Definition

### Recommendation: `VISIBLE_GRID_PRODUCTS` (with `data-productid`)
- **Authoritative Listing Count**: **`VISIBLE_GRID_PRODUCTS`** (40 on initial load).
- **Primary Product Identity in Grid**: The internal `data-productid` attribute (`545425987`), which maps directly to the physical Zara product entity and matches `source_product_id` used in normalized products.
- **Secondary Evidence**: The commercial reference code (`-p01067703.html`) and product URL, tracked strictly in a separate `product_links` field and never mixed into the numerical catalogue ID set.
- **ItemList Exclusion**: `ITEMLIST_PRODUCTS` (10) should be retained purely as corroborating structured-data evidence that the page is a product listing, but must **never** be used as the authoritative product count because Zara caps it at 10 items.

---

## 4. Engineering Adjustments Implemented
1. **Separated Identity Namespaces**:
   - `data-productid` values are stored exclusively in `catalogue_product_ids`.
   - URL reference tokens are stored exclusively in `commercial_ref_tokens`.
   - The merged set of 79 has been removed from crawler output.
2. **Container Scope Enforcement**:
   - Product queries are scoped strictly to the `.product-grid` container to prevent any future pollution from recommendation carousels or editorial banners.
