# Zara US public-site research

Research date: 2026-09-06. Status: partial; product sampling stopped at the terms review gate.

## Scope and evidence

The pasted task's final FIRST TASK governs this delivery: Phase 1 and Phase 2 research and a proposed schema only. The supplied voice-assistant handbook describes the eventual destination, not instructions to build it now. No website, database, scraper or commerce integration was implemented.

PUBLICLY OBSERVED means returned by the public web-reading tool in this session. This is extracted page text, not a verified browser screenshot or raw HTTP response. INFERRED identifies interpretation. SYNTHETIC DESIGN identifies our own proposed model. NOT VERIFIED means evidence is insufficient. Retrieval date does not guarantee catalogue freshness or purchase availability.

## Current navigation and taxonomy

PUBLICLY OBSERVED — The [US homepage](https://www.zara.com/us/) exposes Woman, Man, Kids, Zara Home, Beauty, Massimo Dutti, Pre-Owned and Travel Mode. Examples include women's dresses, jeans, knitwear and shirts; men's shirts, pants, suits and shoes; children's age-group navigation; and home furniture, lighting and bed linens. Beauty includes makeup, perfumes and hair. Editorial collections and promotional navigation coexist with merchandise categories. Stores, gift cards, help and contact labels are present.

INFERRED — Model category membership separately from editorial collection membership. These navigation labels are not evidence of Zara's internal category tables. A label alone does not establish a working destination or stocked assortment.

## Category discovery register

PUBLICLY OBSERVED — The following ten labels were found in homepage navigation; only the two URLs below were opened as category pages. Remaining URLs are NOT VERIFIED and deliberately not reconstructed.

| Department | Category | Observed destination |
|---|---|---|
| Woman | Dresses | https://www.zara.com/us/en/woman-dresses-l1066.html |
| Woman | Jeans | NOT VERIFIED |
| Woman | Knitwear | NOT VERIFIED |
| Woman | Shirts / blouses | NOT VERIFIED |
| Man | Shirts | https://www.zara.com/us/en/man-shirts-l737.html |
| Man | Pants | NOT VERIFIED |
| Man | Suits | NOT VERIFIED |
| Man | Shoes | NOT VERIFIED |
| Home | Furniture | NOT VERIFIED |
| Home | Lighting | NOT VERIFIED |

## Product cards and detail coverage

PUBLICLY OBSERVED — The [men's shirts listing](https://www.zara.com/us/en/man-shirts-l737.html) returned linked product names, dollar-formatted prices, NEW labels, repeated links and image links on static.zara.net. Repeated occurrences sometimes used different names for the same link. No product dataset was saved.

INFERRED — Card count must not be equated with unique product count. Preserve conflicting labels as observations and reconcile against an accessible detail page. A currency symbol alone should not be treated as machine-readable ISO currency evidence.

NOT VERIFIED — A clicked product detail link returned a web-tool internal error. Its HTTP status and cause were unavailable. This does not establish an anti-bot block or that all product pages fail.

| Requested field / feature | Result and acquisition method |
|---|---|
| Name | PUBLICLY OBSERVED at listing-link level; not reconciled to detail heading |
| Department / category | PUBLICLY OBSERVED listing context; individual product membership requires preserved link evidence |
| Price | PUBLICLY OBSERVED dollar text near cards; not verified as final variant price |
| ISO currency | NOT VERIFIED from structured metadata |
| Public product URL / reference / SKU | Product links observed, but exact destination and identifiers not retained as a sample |
| Description | NOT VERIFIED at product-detail level |
| Composition / materials / care | NOT VERIFIED; never derive percentages from a product name |
| Colors / source color codes | NOT VERIFIED |
| Sizes / size codes / size systems | NOT VERIFIED; navigation age groups do not establish sellable size options |
| Sale / compare-at price | Promotional navigation observed; product-level paired prices NOT VERIFIED |
| Image URL / gallery order / variant mapping | Host-level links observed; exact reusable product-image associations NOT VERIFIED |
| Online stock / store stock | NOT VERIFIED; no authoritative inventory lookup performed |
| JSON-LD / embedded JSON / metadata | NOT VERIFIED; extracted text cannot establish raw HTML structure |
| Search | Working search route, filters, results and request contract NOT VERIFIED |

PUBLICLY OBSERVED — The [store-locator page](https://www.zara.com/us/en/z-stores-st1404.html) was retrievable. Store search interactions, geolocation behavior, store hours and product availability were NOT VERIFIED. Help/contact labels were observed; their workflows were not exercised.

## Sample status and stopping condition

Requested: 50–100 products. Delivered: **0 persisted product records**. This is an incomplete sample, not a successful extraction and not evidence that the catalogue is empty.

PUBLICLY OBSERVED — The homepage-linked [terms, section 17, PDF page 15](https://static.zara.net/static/pdfs/US/terms-and-conditions/terms-and-conditions-en_US-20250829.pdf) restrict saving site materials and commercial use unless otherwise permitted. INFERRED — Under the user's explicit instruction to respect terms, permission for this research dataset has not been established, so systematic collection should not proceed. This is a project collection decision, not a legal opinion.

No copied product descriptions, downloaded images, raw-page archive or synthetic records masquerading as Zara data are included. See the access report for technical limits and the schema proposal for work that can proceed independently of Zara.
