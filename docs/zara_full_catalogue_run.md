# Full catalogue discovery run — 2026-09-06

## Result

Incomplete discovery, not a numeric cutoff. No new product detail pages were collected: the user's prerequisite is category-tree discovery first. The 51 existing product records remain intact. The pilot listings contain 58 distinct product-reference URLs, leaving 7 pending core detail captures.

The global menu opened as a blank panel. This was verified in the browser accessibility tree, DOM snapshot and screenshot; the visible menu contained no department links. An uninformative console error was observed. Its cause is unknown. We did not infer empty Kids, Home or Beauty catalogues from this failure.

Known category pages did work. Recursive traversal of their publicly exposed main-content links discovered 369 unique category URLs before repeated browser inspection timeouts interrupted the run. A fresh tab in the same browser recovered individual page viewing, but the timeouts recurred during continued discovery. This is an inspection-transport failure, **not evidence of a Zara CAPTCHA, rate limit or deliberate access block**. No blocked direct HTTP request was retried.

The graph's relationships are sourced as related links. They do not prove parent-child hierarchy. Route-based department classification is explicitly inferred. Global navigation discovery remains incomplete, and the saved queue has not been exhausted.

## Persisted state

- `data/raw/zara/discovery/`: page URL, title, capture time and observed category links; homepage menu failure evidence.
- `data/zara/checkpoints/discovery.json`: visited URLs and remaining discovery queue, saved after every inspected page.
- `data/zara/unique_products.json`: pilot product registry; identity is reconciled with public JSON-LD productGroupID where captured.
- `data/zara/categories.json` and `.csv`: discovered URLs and completion-state fields.
- `data/zara/category_edges.json` and `.csv`: explicit observed relationships, with parent-child verification false.
- `reports/zara_category_tree.md`: incomplete discovered graph in tabular form.
- `reports/zara_catalogue_coverage.*` and `zara_full_catalogue_validation.*`: counts and unresolved work.

Do not describe 51 products as fully field-complete: core JSON-LD is captured but supplemental care and all-color galleries are not fully audited. Existing records should be enriched on resume rather than recaptured from product 1.

## Category-end method

The decision function is `scripts/zara_research/category_end.py`. It is unit-tested but has **not yet been exercised against a completed live category scan**. No category is reported enumerated by this run.

Record iteration zero, then scroll in viewport-sized steps using normal browser interaction. After every scroll, observe the page and persist the current and cumulative product identities. Accumulate identities across scans so virtualized grids cannot erase products already seen. Prefer explicit verified group/reference identities; preserve card IDs separately until their color/group semantics are reconciled.

At each iteration store category URL, iteration, timestamp, products seen, new unique IDs, current-snapshot duplicates, loading/load-more state, scroll position, viewport/document height and any visible error. Save snapshots outside normalized application data. Follow visible load-more controls if present; never invent pagination parameters or replay hidden endpoints.

Completion requires a post-scroll observation. Accept an explicit empty state, an explicit end at the bottom, or two consecutive settled bottom observations with no new IDs, no loading indicator, no load-more control and no document-height growth. Stagnation in the middle of the page is not an end condition. A challenge ends that branch with TECHNICAL_RESTRICTION; other failures use ERROR. Neither is COMPLETE. Category-empty is never inferred merely from missing DOM cards.

There is no product-count stopping limit. Time-bounded tool batches are communication/checkpoint intervals, not completion conditions. On resumed working access, continue the saved discovery queue, then enumerate discovered categories and process pending and partial detail records. Keep image source URLs unchanged, record resize-equivalence separately, and do not assume width-only URL variants are identical without evidence.

## Rebuild reports without web access

```powershell
python scripts/zara_research/catalogue_progress.py
python -m unittest discover -s tests
```

These commands rebuild registries and reports from saved evidence; they do not perform a crawl. Browser collection in this run was performed through the connected browser tools, not an unattended Python scraper. The earlier SQL staging import is unchanged and remains a pilot import, not full-catalogue output.
