# Revised Zara department coverage

Graph repair checkpoint; **not full-catalogue completion**. All five major landing pages were verified in the normal browser. No product detail was reopened.

| Department | Landing verified | Nodes | Product-bearing | Unresolved classification |
|---|---|---:|---:|---:|
| WOMAN | Yes | 269 | 5 | 263 |
| MAN | Yes | 193 | 2 | 191 |
| KIDS | Yes | 13 | 6 | 6 |
| ZARA HOME | Yes | 19 | 1 | 17 |
| BEAUTY | Yes | 8 | 1 | 6 |
| MASSIMO DUTTI | Yes | 5 | 0 | 4 |
| PRE-OWNED | Yes | 5 | 0 | 4 |
| TRAVEL MODE | Yes | 2 | 0 | 1 |
| UNCLASSIFIED | N/A | 16 | 0 | 16 |

**Enumeration queue: 15 verified product-bearing nodes.** Discovery/classification queue: 509 pending. 369 legacy nodes retained; 530 revised nodes. 1 observed canonical alias merge(s).

## Verified department landings
- [WOMAN](https://www.zara.com/us/en/woman-mkt1000.html)
- [MAN](https://www.zara.com/us/en/man-l534.html)
- [KIDS](https://www.zara.com/us/en/kids-mkt1.html)
- [ZARA HOME](https://www.zara.com/us/en/home-mkt2085.html)
- [BEAUTY](https://www.zara.com/us/en/woman-beauty-mkt1414.html)
- [MASSIMO DUTTI](https://www.zara.com/us/en/massimo-dutti-mkt5753.html)
- [PRE-OWNED](https://www.zara.com/us/en/preowned-mkt5794.html)
- [TRAVEL MODE](https://www.zara.com/us/en/zara-travel-mkt15659.html)

## Kids branches

Girl, Boy, Toddler Girl, Toddler Boy, Baby, and Accessories/Shoes each have a browser-observed product grid. Their breadcrumb paths establish Kids parent links. The Kids landing public page links to Home Kids; the Home Kids product grid was also verified. Age ranges are navigation labels from the public Kids landing, not inferred size enums. Home Kids remains under Zara Home ownership with a Kids cross-link.

## Classification and aliases

Product grid presence is proof of product-bearing status, not category completion. Other verified department landings are NAVIGATION_PAGE based on current visible content; they may still lead to campaigns. Uninspected routes stay UNKNOWN instead of being guessed as SEO or collection pages. Only verified product-bearing nodes enter enumeration. Null flags mean unverified.

Breadcrumb edges establish parent links; related links do not. Unknown parents/depths remain null. Department assignments for unvisited routes are explicitly route-inferred.

Fragments are removed. The observed Beauty makeup v1 URL declares the same-path bare canonical and is recorded as an alias. Unverified v1, page, filter and regional parameters remain distinct. Canonical tags are not used to discard pagination coverage. No route is merged just because its title or numeric suffix matches.

## Queues and preservation

Legacy checkpoint, product registry, and all normalized product files are byte-identical (hash checks recorded in JSON). The three new queues preserve attempts, timestamps, errors and per-item checkpoints. Core-captured products are supplemental-review items, not scheduled for blind re-extraction. Discovery COMPLETE means classification/link inspection only; every node still has enumeration_complete=false.

Use 5–10 page verification batches, checkpoint each item, and close only agent-owned tabs between batches. Resume the persisted queues. Repeated inspection failures remain errors, not claims of site blocking. No blocked HTTP method was used.

## Review stop

Stopped before catalogue enumeration and product extraction as requested. This repair verifies department coverage and prepares queues; it does not certify all SEO/category routes or full graph saturation. Further route classification remains queued. The previous coverage reports describe the earlier run; this report supersedes their unverified-department status.
