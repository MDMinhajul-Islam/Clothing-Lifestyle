# Authorized public catalogue sample

## Current graph-repair checkpoint

Use `python scripts/zara_research/repair_graph.py` to rebuild the repaired category graph and three queues. The legacy `catalogue_progress.py` is guarded against overwriting it. The original discovery checkpoint and product registry remain intact. See `reports/zara_department_coverage.md` for the current verified landings, unresolved classification and enumeration queue. Do not run product normalization as a graph-repair step: its legacy category export predates the repaired graph.

No new product detail crawl was performed during repair. The resume decision function now requires three consecutive stable post-scroll bottom checks without new IDs or height growth, rather than two. Explicit end/empty states still require a post-scroll observation. No category has been certified complete by this repair.

The user confirmed authorization to use Zara catalogue data and images for the prototype. Browser capture resumed on 2026-09-06. No further permission question is required for that same scope.

## Run locally

```powershell
python scripts/zara_research/normalize.py
python scripts/zara_research/build_import.py
```

Python standard library only. These scripts process saved evidence without contacting Zara. JSON and CSV outputs are under `data/normalized/zara`; the second command creates `database/zara_research_sample.sql`. It is a reviewable PostgreSQL **research staging import**, not the final transactional database. It has not been executed against PostgreSQL. It uses product/variant foreign keys and stores source fields in JSONB so unsupported source details are preserved.

Raw captures are in `data/raw/zara`. Each detail file includes its observed URL, UTC capture timestamp, title, public DOM JSON-LD, visible product-info text and DOM image observations. One record also includes a composition/care panel snapshot. Scripts never evaluate JavaScript from the source data.

## Capture method

The connected Edge browser opened known public category pages, stayed in the US market and dismissed a nonbinding privacy notice. Read-only DOM queries extracted `.product-grid-product`, names, `data-productid`, `data-productkey`, `data[data-currency]`, color labels and `script[type="application/ld+json"]`. Each discovered product URL was opened sequentially. Only actual `ProductGroup.hasVariant` records became variants; product recommendations in the DOM were excluded from normalized image association.

This repository does **not** include an unattended HTTP scraper. A direct HTTP probe returned a verification interstitial. No verification endpoint, challenge solution, copied browser cookie, proxy rotation or identity spoofing was used. The existing browser loaded the ordinary pages without a challenge. For unattended whole-catalogue collection, obtain a working approved transport or feed; do not route around the direct-client challenge.

## Coverage

51 detail pages from two listing contexts (men's shirts and women's dresses); not the entire Zara US website. A URL-discovery register from category links is also exported. Kids, Home, Beauty, shoes and other merchandise need additional sampling before the parser can claim coverage for them.

Preserve all original image URL parameters. Transparent placeholders are excluded by deriving normalized images from product JSON-LD. The `loaded` raw field only means the browser observed an image loaded, not that its URL was validated for external hotlink use. No image files were downloaded.

Descriptions, materials, colors, sizes, SKU and prices come from explicitly named JSON-LD properties. Department is inferred from captured listing context. `base_price` is our computed minimum observed variant price, not a source field or a final checkout quote. Compare-at prices remain null. Care is missing for all but the inspected first record. Availability is a **public snapshot**, not authoritative stock. Source coverage is explicitly incomplete.

The SQL import is additive and rerunnable; it does not delete older research records or model stock removal. Use a fresh research schema when an exact standalone snapshot is needed. Do not expose this staging schema or privileged DB credentials directly to a future voice model or frontend.
