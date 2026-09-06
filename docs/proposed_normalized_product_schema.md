# Proposed normalized research product schema

Update 2026-09-06: User authorization was confirmed and 51 public detail pages have now been captured. Public JSON-LD provides explicit group IDs, SKU, colors, sizes, prices, materials and image associations. The earlier lack-of-evidence comments below describe the initial design pass. Actual field mappings and remaining gaps are in `scripts/zara_research/README.md`. The generated PostgreSQL file is a JSONB research staging import, not an implementation of the final normalized transactional schema proposed here.

**SYNTHETIC DESIGN throughout.** Proposal only; no migration, database or crawler has been implemented. This is retailer-neutral and does not describe Zara's internal architecture.

The limited public observations justify product labels, listing associations, price observations and source links. All additional requested fields below are nullable capacity for future evidence, not claims that those fields were found on Zara. Missing does not mean unavailable or out of stock.

## Tables

| Table | Proposed fields |
|---|---|
| products | product_id UUID PK; source text; source_product_id text nullable; name text; slug text; department text nullable; category UUID nullable FK; subcategory UUID nullable FK; collection text nullable; description text nullable; composition text nullable; materials JSON nullable; care text nullable; base_price numeric(12,2) nullable; currency char(3) nullable; product_url text; status text; source_last_seen_at timestamptz |
| product_variants | variant_id UUID PK; product_id UUID FK; source_variant_id text nullable; color_name text nullable; color_code text nullable; size_name text nullable; size_code text nullable; sku_or_reference text nullable; price numeric(12,2) nullable; compare_at_price numeric(12,2) nullable; availability_status text default unknown; variant_url text nullable |
| product_images | image_id UUID PK; product_id UUID FK; variant_id UUID nullable FK; image_url text; image_type text default unknown; position integer nullable; alt_text text nullable; source_last_seen_at timestamptz |
| categories | category_id UUID PK; parent_category_id UUID nullable FK; department text nullable; name text; slug text; source_url text nullable |
| size_systems | size_system_id UUID PK; name text; source text; evidence_id UUID nullable FK |
| size_options | size_option_id UUID PK; size_system_id UUID FK; source_label text; normalized_label text nullable; source_code text nullable; position integer nullable |

Recommended retailer-neutral additions: `product_categories(product_id, category_id, evidence_id)` for multiple listing memberships; `variant_size_options(variant_id, size_option_id)` for explicit size mapping; `color_observations(variant_id, source_color_name, normalized_color_family, evidence_id)` to preserve source wording. These are our provenance/normalization choices, not newly discovered Zara fields.

Do not populate size enums from illustrative examples in the task. Observe each product's actual options first. A kids department age range is not a size enum. Home and accessories may have dimensions or no selectable size; null is valid with a reason.

## Field evidence contract

Use a sidecar `field_observations` table/file: observation_id PK, entity_type, entity_id, field_name, source_url, observed_at UTC, method, locator, source_value, normalized_value, classification and missing_reason. Classification is PUBLICLY OBSERVED, INFERRED, SYNTHETIC DESIGN or NOT VERIFIED. Missing reasons include not_exposed, not_inspected, restricted, retrieval_failed and ambiguous. Preserve source values without claiming normalized labels are source terminology.

| Field family | Allowed derivation once permitted |
|---|---|
| Name / description / care / composition | Visible detail field or corroborated structured property; keep material percentages separate from marketing names |
| Product identity | Explicit public identifier; preserve reference and URL token separately until semantics are confirmed |
| Category / department | Observed breadcrumb or source listing membership; identify inferred assignment |
| Price / currency | Exact displayed or structured value with locator, market and timestamp; no conversion guesses |
| Size / color / availability | Actual selected-option or explicitly associated structured record; no inferred stock from button presence |
| Images | Original exposed URL and explicit owning product/variant; gallery position only if observed; no constructed CDN paths |

## Integrity and semantics

Use partial uniqueness on `(source, source_product_id)` when present. Use source URL deduplication only with conservative, documented normalization; preserve original URLs. Slugs and names are not product identifiers. For variants, enforce `(product_id, source_variant_id)` uniqueness when provided; do not invent upstream SKU IDs.

Prices must be nonnegative finite decimals; currency must be a verified ISO code when present. Do not silently turn missing price into zero. Preserve conflicting prices as observations until variant/market/time scope is resolved. `base_price` is a research observation, never an authoritative checkout quote.

Enforce parent-product agreement for image variant references with a composite FK. Deduplicate images within their association, not globally across products: the same URL can legitimately be shared. Preserve original URL query strings. A missing image position is not zero. Image type remains unknown unless its role is evidenced.

Prevent category cycles. Allow products in multiple categories. Do not merge products solely because names match. Do not create every possible size-color combination from independent option lists. Retain availability as unknown unless its exact scope was observed; do not claim inventory quantities from public labels.

Future validation should report duplicate/conflicting IDs, orphan variants, invalid category links, invalid price/currency, absent product URLs, missing images, duplicate association URLs, wrong-product variant images and missing required variant dimensions. HTTP image checks require permitted access; untested URLs are not passed checks. No validation success report is generated for an uncollected dataset.

## Relationship to the future assistant

The handbook's tool-grounded behavior supports keeping research separate from operational truth. SyntheticDemoAdapter and later retailer adapters can normalize their own data into stable domain contracts. The voice agent calls a gateway and domain services; it never queries this schema directly. Customer, order, shipment, return, refund and inventory-state design belongs to the later approved architecture phase.

## Approval checkpoint

Current work stops before large-crawler or database implementation as explicitly requested in the pasted task. Next decision: use an authorized data source or resolve Zara collection permission, then finish the missing sample evidence. A synthetic catalogue can be designed in the later phase without presenting it as observed Zara data.
