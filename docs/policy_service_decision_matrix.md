# NexGen policy-to-service decision matrix

This matrix reconciles NexGen's synthetic retail services with the 11 captured official Zara US help sources. Zara remains the reference brand only: `policy_reference_brand = Zara` and `policy_usage = REFERENCE_DEMO`. Dynamic order, inventory, refund, loyalty, promotion, incident, and customer facts remain synthetic NexGen backend state.

## Decision matrix

| Area | Reference evidence | Autonomous action | Verification | Confirmation | State check | Refuse or hand off |
|---|---|---|---|---|---|---|
| A. Product discovery and recommendation | Public catalogue; no policy dependency | Search and recommend grounded catalogue products | None | None | Catalogue/recommendation service | Abstain when no grounded result; ask whether to broaden one filter |
| B. Product details, size, material, care | `CareAndComposition`, `MySize`; public product facts | Read documented product attributes and available sizes | None | None | Catalogue product record | Do not guarantee fit or invent missing measurements; offer support when evidence is absent |
| C. Store inventory and pickup | `DeliveryMethods` | Check synthetic store stock | None | None | Inventory service and store ID | Never claim reservation, pickup readiness, or a pickup guarantee from stock alone |
| D. Registered customer identification | Operational authentication model; policy account flows in `EditOrder`, `OrderStatus`, `HowToReturn` | Return masked verification guidance and establish a scoped session after proof | Account identifier plus configured challenge | None | Customer and auth-session records | No private profile, loyalty, or order data before valid transaction-scoped verification |
| E. Guest order verification | Guest management links in `EditOrder`, `OrderStatus`, `HowToReturn` | Establish access to one verified order | Order number plus checkout contact proof | None | Scoped auth session | Guest token cannot access another order or full account history |
| F. Order tracking | `OrderStatus` | Read the verified order's stored shipment state | Registered or guest scoped token | None | Shipment record | Do not expose data from order number alone; missing state may be handed off |
| G. Online cancellation | `EditOrder` | Evaluate NexGen synthetic fulfillment state | Scoped token for the owned/verified order | Required before cancellation write | Current order status immediately before write | No numeric cutoff. Non-cancellable orders offer tracking, return after delivery, or support |
| H. Order modification/address change | `EditOrder`, `DeliveryMethods` | Explain supported reference flow | Private order discussion requires scoped token | Any future mutation would require confirmation | Exact order status | Completed items and shipping method cannot be changed. Address mutation is not implemented; offer support because eligible statuses are unpublished |
| I. Return eligibility | `HowToReturn`, `ReturnSpecialConditions` | Evaluate order status, remaining quantity, and 30 days from online shipment date | Scoped token | None for check | Shipment timestamp and return history | Missing shipment evidence or unknown restriction facts cannot establish final eligibility; offer review |
| J. Return creation | `HowToReturn` | Prepare STORE or DROP_OFF return using verified items | Scoped token | Required before write | Eligibility rechecked before write | STORE is free; DROP_OFF deducts $4.95 per request. Unknown product-condition restrictions require review |
| K. Exchange eligibility | `HowToExchange`, `ReturnSpecialConditions` | Check replacement variant and synthetic stock separately | Scoped token and verified order item | None for availability check | Shared shipment-window check plus variant inventory | Reject safely when original eligibility, restriction facts, variant, or stock cannot be verified |
| L. Exchange creation | `HowToExchange` | Prepare an eligible exchange | Scoped token | Required before write | Eligibility and inventory rechecked | Explain the 14-day reference return condition; do not claim automatic charging unless backend enforcement exists |
| M. Refund status and timing | `Refund` | Report the newest stored synthetic refund state | Scoped token | None | Refund repository | No refund record means no recorded refund. Reference timing is explanatory and never a state guarantee |
| N. Damaged, wrong, or missing item | `FaultyItems`; delivered-not-received steps in `DeliveryMethods` | Capture factual incident details | Scoped token for private order/item context | Required before incident write | Order and item ownership | Promise no refund or replacement. Offer human review; delivered-not-received guidance checks tracking, locations, courier, and the reference 72-hour wait |
| O. Loyalty and promotions | No NexGen policy in captured corpus; synthetic demo programs | Check synthetic program records | Loyalty requires registered verification; public code check stays synthetic | None | Loyalty/promotion record | Label results as demo data and never attribute them to official Zara benefits |
| P. Human handoff/support case | Contact guidance across `FaultyItems`, `DeliveryMethods`, `Refund`, `MySize` | Prepare a least-privilege handoff packet | Required only when private context is attached | Support-case creation requires confirmation | Verified facts and prior tool outcomes | Offer for failed verification, disputes, exceptions, incidents, missing evidence, privacy/fraud risk, or explicit human request |
| Q. Unsupported or legally sensitive request | Corpus boundary and RAG provenance rules | Retrieve cited US/en reference evidence | None for public policy | None | Active RAG evidence | Abstain with `INSUFFICIENT_EVIDENCE`, preserve `REFERENCE_DEMO`, and offer human support; never claim official NexGen policy |

## Implemented customer access model

- Anonymous shopper: public catalogue, product, store search, and policy reference only.
- Registered customer: a valid `TRANSACTION_VERIFIED` access token can read that customer's private profile, loyalty record, and owned orders.
- Guest purchaser: an `ORDER_VERIFIED` token can access only its verified order and items.
- Unverified caller: no private order, refund, return, exchange, incident, loyalty, or profile data.
- Disputed or high-risk case: no automatic adjudication; prepare a least-privilege human handoff.

The current verification data is deterministic and synthetic. Production mapping is: website login to backend access token; guest order to order number plus checkout-contact verification; voice-only caller to a verification challenge. OTP, email, or SMS delivery remains future infrastructure and must not be claimed until configured.

## Evidence-backed operational mappings

- NexGen maps `PENDING`, `CONFIRMED`, and `PROCESSING` to its synthetic cancellable stages. The Zara source only says cancellation depends on status and option availability, so this mapping is not represented as an official Zara status list.
- Online return and exchange windows use 30 days from `shipped_at`. `delivered_at`, `updated_at`, and `placed_at` are not substitute evidence.
- STORE return fee is $0. DROP_OFF return fee is $4.95 per request and is deducted from the estimate. No other fee is inferred.
- The online-exchange reference says replaced merchandise must be returned within 14 days. NexGen may explain this condition but does not claim automatic charging or enforcement.
- Refund service reports stored state. The reference 72-hour facility-processing and bank-dependent maximum timing are explanatory policy facts only.

## Remaining unknowns

The captured corpus does not define NexGen policies, exact internal cancellation/address-change status mappings, production identity challenges, fraud adjudication, wrong-item remedies, support SLAs, or every structured flag needed for special return restrictions. The current product/order schema also does not reliably encode condition, attached labels, hygiene seals, gift receipt, personalized status, pack membership, or every online-exchange payment restriction. The agent must not infer these facts; it should qualify preliminary checks and offer human review.

## Security and provenance constraints

The voice layer validates scoped access before legacy private order tools are dispatched. Tokens, verification values, contact identifiers, and free-text incident details remain redacted from response metadata and audit summaries. The AI/voice layer receives no database credentials or raw SQL access. Public Zara catalogue/policy evidence and synthetic NexGen operational state remain separate in both structured metadata and spoken claims.
