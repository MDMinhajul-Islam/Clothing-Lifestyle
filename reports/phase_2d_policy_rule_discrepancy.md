# Phase 2D policy rule discrepancy audit

Reviewed against repository base 670d705. Existing deterministic rules remain unchanged.
Evidence is official-page research-tool text captured on 2026-09-07; upstream freshness and effective dates are unknown.
Status meanings: MATCH = supported equivalence; MISMATCH = conflicting behavior; PARTIAL = incomplete alignment; UNKNOWN = insufficient evidence.
The legal terms PDF has not been captured; findings are bounded by the help corpus. These are engineering comparisons, not a complete legal review.

## cancellation_eligible_statuses — PARTIAL

**Current:** PENDING, CONFIRMED, PROCESSING are eligible.

**Official evidence:** Cancellation depends on order status and availability of the option; exact internal status mapping is not published.

**Source:** [CHANGE OR CANCEL AN ONLINE ORDER](https://www.zara.com/us/en/help-center/EditOrder)

**Action:** Document a verified fulfillment-state mapping before changing eligible statuses.

## cancellation_timing — UNKNOWN

**Current:** No elapsed-time cutoff exists.

**Official evidence:** The captured help article specifies status-dependent availability, without a numeric time limit.

**Source:** [CHANGE OR CANCEL AN ONLINE ORDER](https://www.zara.com/us/en/help-center/EditOrder)

**Action:** Do not introduce a 30-minute rule; absence of a number is not proof that no other cutoff exists.

## return_window — MISMATCH

**Current:** 30 days from delivered_at.

**Official evidence:** Online returns use shipment date; in-store returns use purchase date.

**Source:** [HOW TO RETURN](https://www.zara.com/us/en/help-center/HowToReturn)

**Action:** Propose channel-aware date anchoring with shipment evidence; leave current rules unchanged.

## fallback_date_logic — MISMATCH

**Current:** Missing delivered_at falls back to updated_at then placed_at.

**Official evidence:** The published online anchor is shipment date; neither fallback establishes shipment.

**Source:** [HOW TO RETURN](https://www.zara.com/us/en/help-center/HowToReturn)

**Action:** Propose unknown eligibility when the authoritative date is absent; never infer shipment from record updates.

## return_quantity — PARTIAL

**Current:** Remaining quantity = ordered minus all prior return_item quantities; requested quantity checked per request entry.

**Official evidence:** Packs cannot be returned separately; the source does not document database counting or duplicate request-entry semantics.

**Source:** [SPECIAL RETURN CONDITIONS](https://www.zara.com/us/en/help-center/ReturnSpecialConditions)

**Action:** Preserve quantity safeguards; separately review duplicate line aggregation, prior return statuses and pack restrictions.

## refund_calculation — PARTIAL

**Current:** Estimate uses discounted line total divided by ordered quantity, multiplied by requested quantity; no channel fee deducted.

**Official evidence:** Drop-off requests incur a fee deducted from refund; in-store returns are free. Tax, discount allocation and rounding are not fully specified here.

**Source:** [HOW TO RETURN](https://www.zara.com/us/en/help-center/HowToReturn)

**Action:** Audit fee application by return channel; retain UNKNOWN for accounting details without further official evidence.

## return_condition_restrictions — MISMATCH

**Current:** No original-condition, labels, market or category checks in ReturnRules.

**Official evidence:** Original condition, labels and same-market requirements apply; the separate conditions article adds category exceptions.

**Source:** [HOW TO RETURN](https://www.zara.com/us/en/help-center/HowToReturn)

**Action:** Propose explicit condition/market checks together with evidence-backed category exclusions.

## category_exclusions — MISMATCH

**Current:** Return eligibility considers status, date and quantities, without category exclusions.

**Official evidence:** Special conditions cover hygiene strips, undergarments, packaging, fragrances, cosmetics, personalized items, HOME, packs and magazines.

**Source:** [SPECIAL RETURN CONDITIONS](https://www.zara.com/us/en/help-center/ReturnSpecialConditions)

**Action:** Design category mapping and exception tests before enforcement changes.

## exchange_rules — PARTIAL

**Current:** Requires return eligibility, replacement variant and available stock.

**Official evidence:** Published exchange conditions additionally cover date anchors, condition, market, product/payment restrictions and online exchange limits.

**Source:** [HOW TO MAKE AN EXCHANGE](https://www.zara.com/us/en/help-center/HowToExchange)

**Action:** Propose channel-specific restrictions and exchange return deadline; do not infer US support for every payment name listed globally on the US page.

## delivery_order_state_assumptions — UNKNOWN

**Current:** Returns require DELIVERED or PARTIALLY_RETURNED; cancellation uses internal uppercase statuses.

**Official evidence:** Public order tracking describes purchase, processing, preparation, shipment, courier and delivery stages, without an internal-code mapping.

**Source:** [STATUS OF MY ONLINE ORDER](https://www.zara.com/us/en/help-center/OrderStatus)

**Action:** Document mapping and separate delivery evidence from the online return-window anchor.

## refund_processing — PARTIAL

**Current:** Refund service reads synthetic stored status; no official processing SLA enforcement.

**Official evidence:** The help article describes processing after facility receipt and subsequent bank-dependent credit timing.

**Source:** [RETURN REFUND](https://www.zara.com/us/en/help-center/Refund)

**Action:** Use RAG to explain published timing; use the gateway for actual synthetic refund status.
