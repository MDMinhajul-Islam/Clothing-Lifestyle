# Antigravity Project Handoff

## 1. Project Goal

Build a realistic Zara-style clothing and lifestyle e-commerce prototype backed by public catalogue research. The intended later system includes a normalized PostgreSQL/Supabase data model, backend domain services, an AI Tool Gateway, an AI voice assistant, Docker, and Dokploy deployment. The assistant must use tools and domain services for operational truth rather than treating research files or model memory as live inventory, order, shipment, return, or refund state.

The current research preserves public Zara US product facts and public image URLs for an authorized prototype. It does not claim ownership of Zara content, private access, live inventory accuracy, or full-catalogue coverage.

## 2. Current Phase

We are still in **PHASE 1: Zara Public Catalogue Research**.

Do **not** start website implementation yet.

Do **not** start Supabase yet.

Do **not** start AI agent integration yet.

Do **not** start FAQ/policy research yet.

## 3. Work Completed So Far

- Initial public-site research documented accessible catalogue evidence, constraints, and provenance rules.
- A validation sample captured 51 unique public product detail pages from men's shirts and women's dresses.
- Public `ProductGroup` JSON-LD supplied explicit product-group IDs, variant SKU/reference values, names, descriptions, colors, sizes, prices, currencies, materials, availability labels, product URLs, and product/variant image associations where present.
- Visible page markup supplied listing cards, category links, listing membership, DOM image observations, product-info text, and one inspected composition/care panel snapshot. Recommendations were excluded from normalized product images.
- Normalization produced 51 products, 425 explicit variants, 825 product/variant image associations, and 444 unique public image URLs. Validation reports no current normalization errors, products without images, or products without a captured category.
- A pilot category pass discovered 369 category URLs and inspected 39 pages before browser-inspection timeouts interrupted it.
- The offline graph repair retained all 369 legacy nodes and expanded the graph to 403 nodes using saved browser evidence. It classified 11 nodes as `PRODUCT_LISTING_CATEGORY`, 7 as `NAVIGATION_PAGE`, and left 385 `UNKNOWN`.
- All five major department landings (Woman, Man, Kids, Zara Home, Beauty) were verified through normal browser access. Additional Massimo Dutti, Pre-Owned, and Travel Mode landing routes were also observed.
- Kids Girl, Boy, Toddler Girl, Toddler Boy, Baby, and Accessories/Shoes were verified as product grids. Home Kids was also verified as a product grid.
- Persistent discovery, enumeration, and product-detail queues were created. Existing product data, the legacy discovery checkpoint, and the product registry were preserved byte-for-byte during graph repair.
- Canonicalization removes fragments and records only conservatively verified same-path canonical aliases. One observed Beauty URL alias was merged. Pagination, filters, regions, cross-path canonicals, and unobserved query variants remain distinct.
- Breadcrumb evidence creates parent links. Related links remain non-hierarchical. Route-based department assignments are marked as inferred.
- Category-end logic was strengthened and unit tested. The full suite currently passes 13 tests.

## 4. Current Data Status

| Metric | Verified count |
|---|---:|
| Unique products | 51 |
| Explicit variants | 425 |
| Unique public image URLs | 444 |
| Product/variant image associations | 825 |
| Category nodes | 403 |
| Confirmed product-bearing listings | 11 |
| Pending discovery/classification queue items | 387 |
| Product detail queue records | 58 |
| Preserved partial product records | 51 |
| Unseen product detail pages queued | 7 |

These counts are a preserved validation sample and repaired discovery graph. They are **not** the full Zara catalogue. No category has yet been certified as fully enumerated.

## 5. Department Status

| Department | Nodes | Confirmed product-bearing | Discovery status | Remaining work |
|---|---:|---:|---|---|
| Woman | 183 | 1 | Landing verified; 181 routes unresolved | Classify unresolved routes, then enumerate verified listings |
| Man | 187 | 2 | Landing verified; 185 routes unresolved | Classify unresolved routes, then enumerate verified listings |
| Kids | 13 | 6 | Landing and requested branches verified; 6 routes unresolved | Classify remaining routes and enumerate six known listings |
| Zara Home | 6 | 1 | Landing and Home Kids verified; 4 routes unresolved | Classify remaining routes and enumerate Home Kids |
| Beauty | 7 | 1 | Landing and Makeup listing verified; 5 routes unresolved | Classify remaining routes and enumerate Makeup |
| Other/unclassified | 7 | 0 | Three observed navigation landings; 4 routes unresolved | Retain boundaries and classify the four unknown routes if relevant |

“Other/unclassified” aggregates Massimo Dutti (1 node), Pre-Owned (1), Travel Mode (1), and `UNCLASSIFIED` (4). The graph has 385 `UNKNOWN` nodes overall. The discovery queue has 387 pending items because queue completion records link inspection/classification work and does not map one-to-one to the current route-type count.

## 6. Current Queue State

- `data/zara/category_discovery_queue.json`: 403 records; 387 `QUEUED`, 16 `COMPLETE`. This is the queue to resume first. Each entry stores ID, URL, status, attempt count, last attempt, error, and classification checkpoint evidence.
- `data/zara/category_enumeration_queue.json`: 11 verified product-bearing routes; all 11 are `QUEUED`. Each begins with `phase=enumeration`, `scroll_iteration=0`, and an empty `seen_product_ids` list.
- `data/zara/product_detail_queue.json`: 58 records; 51 `PARTIAL` records preserve completed core extraction and require supplemental validation only, while 7 `QUEUED` records have not received core detail extraction.

`data/zara/checkpoints/discovery.json` is the preserved legacy checkpoint with visited and remaining routes. `data/zara/checkpoints/latest.json` and the per-item queue checkpoint objects retain earlier progress. `data/zara/checkpoints/pre_graph_repair/` holds the pre-repair category, edge, discovery, and product-registry snapshots. The repair script writes JSON atomically through a `.tmp` file and preserves prior queue attempt/status/checkpoint values by stable IDs. Browser work must persist each small batch back to these queue/state files so a timeout resumes at the failed or next queued item rather than rebuilding the graph.

## 7. Important Files

| Class | Path | Purpose | Current state |
|---|---|---|---|
| A — source code | `scripts/zara_research/repair_graph.py` | Offline graph repair, conservative canonicalization, queue construction, category/report export, and protected-file hash checks | Current graph builder; safe to rerun against retained evidence |
| A — source code | `scripts/zara_research/category_end.py` | Pure category completion decision function | Current implementation requires three stable post-scroll bottom observations |
| A — source code | `scripts/zara_research/normalize.py` | Converts saved product/listing JSON-LD evidence into normalized JSON/CSV and validation reports | Current product normalizer; skips category export when repaired graph exists |
| A — source code | `scripts/zara_research/build_import.py` | Generates a reviewable PostgreSQL research-staging SQL import | Does not connect to a database |
| A — source code | `scripts/zara_research/catalogue_progress.py` | Earlier offline registry/report builder | Guarded: exits when repaired graph exists because it would overwrite repaired categories |
| A — runbook | `scripts/zara_research/README.md` | Capture method, limitations, offline commands, and data semantics | Current for the repaired graph; read with this handoff |
| B — raw research output | `data/raw/zara/*.json` | 51 product captures plus two pilot listing captures | Preserved; public JSON-LD, visible text, DOM observations, URL, and timestamp |
| B — raw research output | `data/raw/zara/discovery/*.json` | Earlier inspected route/link observations, including blank-menu evidence | Preserved historical evidence |
| B — raw research output | `data/raw/zara/repair/*.json` | Department and branch observations used by graph repair | Preserved current repair evidence |
| C — normalized data | `data/normalized/zara/products.{json,csv}` | 51 normalized product records | Validated sample, incomplete catalogue |
| C — normalized data | `data/normalized/zara/product_variants.{json,csv}` | 425 explicit JSON-LD variants | Validated sample |
| C — normalized data | `data/normalized/zara/product_images.{json,csv}` | 825 associations and 444 unique source URLs | URLs retained with original parameters; network/hotlink validation not run |
| C — normalized data | `data/normalized/zara/product_categories.{json,csv}` | Product-to-category memberships | Preserved from pilot normalization |
| C — normalized data | `data/normalized/zara/product_materials.{json,csv}` | Explicit material observations | Preserved; coverage varies by product |
| C — normalized data | `data/normalized/zara/categories.{json,csv}` | Repaired 403-node category export | Owned by graph repair, not legacy normalizer |
| D — checkpoint/state | `data/zara/category_graph.json` | Persistent graph: 403 nodes and observed edges | Authoritative current graph checkpoint |
| D — checkpoint/state | `data/zara/categories.{json,csv}` | Repaired category rows | Current graph export |
| D — checkpoint/state | `data/zara/category_edges.{json,csv}` | Breadcrumb, related-link, and observed cross-link edges | Current graph export |
| D — checkpoint/state | `data/zara/category_discovery_queue.json` | Discovery/classification work queue | 387 queued, 16 complete |
| D — checkpoint/state | `data/zara/category_enumeration_queue.json` | Verified listing enumeration queue | 11 queued |
| D — checkpoint/state | `data/zara/product_detail_queue.json` | Core and supplemental detail work | 51 partial, 7 queued |
| D — checkpoint/state | `data/zara/unique_products.json` | Pilot global product registry | 58 unique product references; 51 core-extracted and 7 pending |
| D — checkpoint/state | `data/zara/checkpoints/` | Legacy, latest, and pre-repair resume snapshots | Preserved and committed |
| D — checkpoint/state | `data/zara/url_aliases.json` | Verified URL-to-canonical mappings | One conservative observed merge |
| D — checkpoint/state | `data/zara/category_scans.json` | Earlier category scan observations | Historical/incomplete; no category certified complete |
| D — errors | `data/zara/browser_errors.json`, `data/zara/errors.json` | Browser/research error records | Preserve and append failures rather than hiding them |
| E — generated report | `reports/zara_department_coverage.{md,json}` | Latest repaired department, route, queue, and integrity summary | Primary current coverage report |
| E — generated report | `reports/zara_category_tree.md` | Human-readable repaired graph | Current; parent values appear only with evidence |
| E — generated report | `reports/zara_research_validation.{md,json}` | Product normalization counts and integrity findings | Current: 51/425/444, zero listed errors |
| E — historical report | `reports/zara_catalogue_coverage.{md,json}` | Earlier 369-node discovery-run coverage | Superseded where it conflicts with department coverage report |
| E — historical report | `reports/zara_full_catalogue_validation.{md,json}` | Earlier incomplete full-catalogue attempt validation | Historical; does not certify catalogue completeness |
| E — generated import | `database/zara_research_sample.sql` | Additive research-staging SQL for current sample | 0.86 MB; generated but never executed |
| E — documentation | `docs/zara_public_site_research.md` | Public-site evidence and research boundary | Current supporting research |
| E — documentation | `docs/zara_data_access_research.md` | Data-access findings and constraints | Current supporting research |
| E — documentation | `docs/proposed_normalized_product_schema.md` | Proposed retailer-neutral schema and evidence contract | Design document, not a migration |
| E — documentation | `docs/zara_full_catalogue_run.md` | Narrative of the earlier interrupted discovery run | Historical; its two-check end-condition text predates the current three-check implementation |
| F — tests | `tests/test_category_end.py` | Initial-view, stagnation, stable-bottom, loading/height, and restriction behavior | Passing |
| F — tests | `tests/test_graph_repair.py` | Canonicalization and department precedence | Passing |
| F — tests | `tests/test_zara_normalizer.py` | Price validation and JSON-LD graph traversal | Passing |

There is no `config/` directory and no separate crawler/browser-helper program. Browser capture was performed through the connected browser automation environment. All safe raw/state artifacts fit comfortably in Git: the repository has about 7.35 MB of files, and the largest file is `database/zara_research_sample.sql` at about 0.86 MB. No research output needs to remain local-only for size reasons.

## 8. Current Crawler Strategy

- Use normal public browser access only. Stay on public Zara pages in the selected market.
- Do not bypass CAPTCHA, authentication, access controls, or verification challenges.
- The global menu was unreliable and appeared as a blank panel, so known department landing pages and their visible public links were used.
- Treat `data/zara/category_graph.json` as persistent state. Enrich it incrementally; do not rebuild the project from scratch.
- Canonicalize conservatively. Remove fragments, accept an observed same-host/same-path canonical only under the implemented rules, and keep unverified pagination/filter/region variants distinct.
- A product appearing in several categories must create one product record and multiple product-category relationships.
- Prefer explicit `source_product_id`/`productGroupID`, then a verified group/reference identity, for global deduplication. Keep card IDs and URLs as evidence until their semantics are reconciled.
- Capture in small browser batches and save after every batch. A browser failure pauses that item; it does not erase the queue or prove the route is blocked.

## 9. Known Problems / Limitations

- Browser DOM/accessibility inspection timed out repeatedly during the earlier long run. Opening a fresh tab restored individual inspection, but timeouts recurred.
- The global menu opened as a blank panel with no useful department links. Its cause remains unknown.
- The graph remains incomplete: 385 routes are `UNKNOWN`, and 387 discovery/classification queue records are pending.
- Only 11 routes are currently confirmed product-bearing.
- Catalogue enumeration and product-detail extraction are incomplete. No category has been certified fully enumerated.
- Kids, Zara Home, and Beauty were absent from the first discovery snapshot; their department landings and specified product-bearing branches are now verified, but their broader route classification remains incomplete.
- Direct Python HTTP requests encountered an Akamai verification interstitial. Do not pursue that blocked direct-request path or use it to bypass browser restrictions.
- Do not infer category completion from the initial viewport. Virtualized or lazy-loaded grids may remove or add visible cards while scrolling.
- Product totals across category pages contain duplicates because products can belong to New, Collection, product-type, and Special Prices routes.
- The 51 product records have core JSON-LD capture, but supplemental care/composition panels and all-color gallery coverage are not complete for every item.
- Public availability is a timestamped observation, not authoritative inventory. Image URLs are stored but external hotlink/network validity has not been tested.
- `docs/zara_full_catalogue_run.md` describes the earlier two-stable-check rule and lists `catalogue_progress.py`; both are superseded by `category_end.py`'s three-check rule and the repaired-graph guard.
- There is no unattended live crawler or queue-resume CLI in this repository. Antigravity must implement or operate a browser-based small-batch worker around the existing files without replacing their schema or losing checkpoints.

## 10. Tests

Run:

```powershell
python -m unittest discover -s tests
```

Current verified result on 2026-09-06 with Python 3.14.7: **13 passed, 0 failed, 0 skipped**.

- `tests/test_category_end.py`: five tests for initial viewport exclusion, middle-page stagnation, three stable post-scroll bottom checks, loading/document-height growth, and technical restrictions.
- `tests/test_graph_repair.py`: five tests for query preservation, observed same-path aliases, cross-host/path rejection, fragment removal, and department precedence.
- `tests/test_zara_normalizer.py`: three tests for invalid price rejection, nullable/decimal price normalization, and JSON-LD graph traversal without promoting variants to groups.

## 11. What Must Happen Next

Antigravity's next job is **PHASE 1A — finish category graph classification**.

Then complete **PHASE 1B — enumerate all verified product-bearing categories**.

Then complete **PHASE 1C — process all unique product detail pages**.

Then complete **PHASE 1D — full validation and coverage report**.

Only after those steps may work begin on **PHASE 2 — Zara Help / FAQ / Policy / Business Rule extraction**.

Do **not** jump to Phase 2 yet.

## 12. Exact Next Algorithm

1. Load the existing graph and checkpoints, especially `data/zara/category_graph.json` and all three queue files.
2. Resume the 387-item discovery/classification queue.
3. Process small batches, such as 5–10 routes per browser session.
4. Classify each route as `PRODUCT_LISTING`, `COLLECTION/CAMPAIGN`, `SEO_LANDING`, `NAVIGATION`, `HELP/OTHER`, or `UNKNOWN`. Map these labels carefully to existing stored fields; preserve `UNKNOWN` when evidence is insufficient.
5. Update the persistent graph and queue after each batch, including attempt count, timestamp, evidence, error, and discovered edges.
6. Add verified product-bearing pages to the enumeration queue exactly once.
7. Enumerate product IDs until the category end condition in section 13 is satisfied.
8. Deduplicate products globally using the rules in section 14.
9. Add unseen products to the product-detail queue. Do not blindly reopen the 51 core-preserved products.
10. Extract queued detail pages and perform targeted supplemental review of partial records.
11. Persist every batch atomically and retain raw evidence.
12. Resume after browser failure instead of restarting discovery.
13. Regenerate and review coverage metrics continuously; report blocked and unresolved routes separately from complete routes.

## 13. Category Completion Logic

The current implementation is `scripts/zara_research/category_end.py::completion_reason`.

A category can complete only after at least one post-scroll observation. The function returns:

- `CATEGORY_EMPTY` when a post-scroll observation explicitly identifies an empty category, zero products were seen, and no loading/load-more state exists.
- `END_OF_LIST` when a post-scroll observation explicitly identifies the end, the viewport is at the bottom, and no loading/load-more state exists.
- `NO_NEW_PRODUCTS` after **three consecutive settled post-scroll bottom observations** with zero new unique product IDs, no loading indicator, no load-more control, and one stable document height. At least one product must have been seen. In practice, the observation list must include the initial state plus these three post-scroll checks.
- `TECHNICAL_RESTRICTION` when the latest observation reports a restriction.
- `ERROR` when the latest observation reports an error.

`TECHNICAL_RESTRICTION` and `ERROR` are terminal observations for the attempt, but they are **not** `COMPLETE`. Stagnation away from the bottom is not completion. The browser worker must accumulate identities across iterations so virtualized grids cannot erase previously seen products. The older two-check wording in `docs/zara_full_catalogue_run.md` is historical and must not be used.

## 14. Deduplication Rules

The same product may appear in `NEW`, `COLLECTION`, `T-SHIRTS`, `SPECIAL PRICES`, or other listing routes. Store the product once and maintain its listing memberships separately in `product_categories` and graph/evidence records.

Unique-key priority:

1. Explicit source plus `productGroupID`/`source_product_id`.
2. Explicit verified group/reference identity when product-group ID is unavailable.
3. Source product URL only under conservative documented URL normalization.

Do not merge by name, slug, image URL, category card position, or numeric URL suffix alone. Preserve source variant IDs/SKUs within the parent product. Do not generate a Cartesian product from independent color and size lists; normalize only explicit `ProductGroup.hasVariant` entries. Image rows deduplicate by exact product, optional variant, and source URL association rather than globally across all products.

## 15. Product Extraction Contract

Capture and preserve these fields where publicly available:

- product ID and source product group ID
- variant ID and SKU/reference
- name and description
- department and all observed category memberships
- price, currency, and timestamped availability label
- colors, sizes, and explicit variants
- composition/material and care text
- product URL and exact public image URLs
- evidence file, method, source timestamp, classification, and completeness note

Current JSON-LD mapping:

- `ProductGroup.productGroupID` → source product ID.
- `ProductGroup.name`, `description`, `material`, `additionalProperty`, `url`, and `image` → group-level product fields.
- `ProductGroup.hasVariant[]` plus each variant's `sku`, `color`, `size`, `image`, and `offers` → explicit variants, variant images, price, currency, availability, and variant URL.

Current visible-markup/raw evidence mapping:

- Listing cards and category links → product discovery and category membership.
- `data-productid`, `data-productkey`, visible product-info text, color labels, and DOM image observations → preserved corroborating evidence.
- An opened composition/care panel → supplemental care evidence for the one inspected record.

Department is currently inferred from captured listing membership where an explicit structured department is absent. `base_price` is the minimum observed variant price only when one currency is present; it is not a source field or checkout quote. Compare-at price remains null unless explicitly observed.

## 16. Safety / Access Constraints

- Use public browser access only.
- Do not bypass CAPTCHA or verification challenges.
- Do not bypass authentication or access controls.
- Do not use private APIs or hidden endpoints.
- Do not collect private customer data.
- Stop the affected route and record technical restrictions or errors with evidence.
- Do not use the previously blocked direct HTTP method to bypass browser restrictions.
- Do not copy browser cookies, session storage, profiles, or credentials into the repository.

## 17. Definition of Phase 1 Complete

Phase 1 is complete only when:

- all discoverable major departments are mapped;
- category nodes are classified as far as normal public access permits;
- every verified product-bearing route is enumerated to a reliable end condition;
- unique public products are processed through the detail queue;
- variants and image associations are normalized;
- duplicate products are resolved while category memberships remain intact;
- incomplete, failed, ambiguous, and blocked routes are reported honestly;
- final catalogue validation passes; and
- a final coverage report is generated.

Completeness is not an arbitrary product number. Technical restrictions and unresolved routes must remain visible in the completion report.

## 18. Phase 2 Preview

After Phase 1 catalogue completion, Phase 2 will collect and classify public Zara help-centre content, FAQs, return and exchange rules, refund and cancellation policies, shipping, payment, pricing policy, size/care knowledge, and legal/privacy/accessibility material. It will distinguish reference knowledge from deterministic operational rules.

**NOT YET.**

## 19. Environment / Runbook

- OS: Windows (PowerShell).
- Working directory: `F:\NEXVIX INTERN\Clothing Lifestyle`.
- Verified Python: Python 3.14.7 at `C:\Python314\python.exe`.
- Python dependencies: standard library only for the current scripts. There is no requirements file and no repository virtual environment.
- Environment activation: none required. If Antigravity creates a virtual environment for its own browser worker later, keep it in `.venv/` and do not commit it.
- Browser dependency: the existing evidence was captured through a connected Edge browser/browser-automation tool using ordinary public pages. There is no packaged Selenium/Playwright dependency or unattended crawler in this repository.

Verified commands from the repository:

```powershell
# Run all tests
python -m unittest discover -s tests

# Rebuild repaired graph, queues, category exports, and department/tree reports offline
python scripts/zara_research/repair_graph.py

# Rebuild normalized product sample and product validation report offline
python scripts/zara_research/normalize.py

# Rebuild the reviewable SQL research-staging import offline
python scripts/zara_research/build_import.py
```

Do not run `python scripts/zara_research/catalogue_progress.py` while the repaired graph exists; it intentionally exits to prevent overwriting repaired categories.

There is **no actual live resume command** in this repository. Browser capture was interactive through the connected browser tools. The first implementation task is to create or operate a normal-browser small-batch queue worker that reads `data/zara/category_discovery_queue.json`, preserves the existing schemas/checkpoints, and follows sections 8, 12, 13, and 16. Do not substitute direct HTTP requests. Report generation is performed by `repair_graph.py` for category coverage/tree and `normalize.py` for product validation.

## 20. Git State at Handoff

- Branch at document creation: `main`.
- Pre-handoff last commit: `114a594b01d46277c8e4b289c5d2260696bf843e` — `web scrapiing`.
- Remote: `origin` → `https://github.com/MDMinhajul-Islam/Clothing-Lifestyle.git` (fetch and push).
- Intended handoff commit message: `Checkpoint Zara catalogue research and add Antigravity handoff`.
- Push result at document creation: pending final commit/push verification.

A Git commit cannot embed its own final hash, and a push result cannot be recorded inside that immutable commit before it is pushed. After checkout, use `git branch --show-current`, `git log -1 --oneline`, and `git status` to obtain the exact pushed handoff commit and verify a clean tree. The exact resulting commit hash and push result are also supplied in the final Codex handoff response.
