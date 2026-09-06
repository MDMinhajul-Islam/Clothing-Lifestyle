# Zara data-access research

Research date: 2026-09-06. Phase 2 is partial: public text access verified; browser network architecture NOT VERIFIED.

## Observed sources and decisions

| Source | Method / parameters | Public response observed | Authentication | Reliability / decision |
|---|---|---|---|---|
| https://www.zara.com/us/ | Public page open, no supplied parameters | Navigation labels and links | No login used | Useful for bounded navigation research; not an API contract |
| https://www.zara.com/us/en/man-shirts-l737.html | Public page open, no supplied parameters | Product-link labels, displayed dollar prices, NEW badges, image links | No login used | Extracted text readable; duplicates and label conflicts require reconciliation |
| https://www.zara.com/us/en/woman-dresses-l1066.html | Public page open, no supplied parameters | Retrievable category document | No login used | Detail completeness not assessed |
| https://www.zara.com/us/en/z-stores-st1404.html | Public page open | Retrievable store page | No login used | Store interaction and stock not tested |
| Product link from shirts listing | Public click | Tool internal error | No login used | Cause and HTTP status unknown; no broad availability conclusion |
| https://www.zara.com/robots.txt | Public page open | Crawler directives | No login used | Reviewed before considering collection |

PUBLICLY OBSERVED applies to the source observations above. The web tool reports HTML/text content but does not expose an origin request trace. GET is the expected normal document retrieval method (INFERRED), not a captured network fact.

For every product data source above: pagination parameters, stable product IDs, sellable variant IDs, structured image fields, structured price fields and size/color fields are **NOT VERIFIED**. Category association is only the page context. No authentication requirement beyond anonymous page reading was tested.

## Raw transport and browser inspection limits

PUBLICLY OBSERVED — One local PowerShell Invoke-WebRequest attempt to the already discovered shirts URL failed with a connection-refused error. No response body or status was obtained. INFERRED — This may be an environment transport restriction; it is not evidence of Zara rejecting the request. No alternate proxy, identity spoofing or control bypass was attempted.

NOT VERIFIED — Browser DOM, XHR/fetch trace, GraphQL, REST product service, JSON-LD, embedded state, script payload shape, caching headers, pagination and rate-limit thresholds. No browser network capture was performed. A readable web-tool extraction cannot distinguish server-rendered HTML from client-rendered content or cached tool extraction.

No stable public catalogue API was established. No endpoint has been invented or replayed. Endpoint-looking strings in robots.txt are restrictions, not discovered working APIs.

## Robots and terms gate

PUBLICLY OBSERVED — [robots.txt](https://www.zara.com/robots.txt) disallows availability and sizing-info routes under itxrest, size-guide paths, user/guest/cart paths and several query patterns including color and rows. It also lists a sitemap. These directives do not establish permission to collect every other route. No restricted route or sitemap was fetched for catalogue collection.

PUBLICLY OBSERVED — The homepage links [US terms](https://static.zara.net/static/pdfs/US/terms-and-conditions/terms-and-conditions-en_US-20250829.pdf). Section 17 on PDF page 15 restricts saving materials and commercial use absent permission. INFERRED — The requested dataset lacks an established permitted collection basis. Stop bulk and sample harvesting rather than changing transport to obtain the same material.

No 429 response, Retry-After header, measurable throughput limit or CAPTCHA was observed. This does **not** imply unlimited access. No requests were made to validate product image URLs; image reliability, signing, expiration and hotlink behavior remain NOT VERIFIED.

## Safest extraction strategy

SYNTHETIC DESIGN — Obtain a retailer-authorized export/feed or use an explicitly licensed dataset for repeatable development. Keep the final demo synthetic, as requested. For Zara, resolve dataset permission before collecting 50–100 records. User approval to implement alone does not establish retailer permission.

Conditional proposal, not implementation: if collection is permitted, prefer ordinary discovered public pages with explicit provenance; inspect JSON-LD only when actually present and corroborate it with visible fields. Do not assume browser-called endpoints are supported public APIs. Start with ten category contexts and fifty unique detail pages, one request at a time, at least five seconds apart, with a hard request budget and immediate stop on access denial or challenge. These are conservative project limits, not observed Zara rate limits.

Preserve permitted source evidence and normalized output separately. Record original URL, UTC retrieval time, source type, field locator and missing-value reason. Never fabricate a color-size Cartesian product. Recheck permission and robots before each run; do not probe excluded availability services. Live stock and final price for the eventual assistant must come from an authorized provider through backend services.

## Completion gaps

The site structure findings are partial, the sample has zero persisted records, and no verified data API is available. Before a collection implementation can be approved, establish a permitted data source and complete detail-page, variant, price and image evidence checks. The proposed schema is in `proposed_normalized_product_schema.md`; it is our design, not a reverse-engineered Zara database.
