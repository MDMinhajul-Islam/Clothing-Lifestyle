# Phase 2G.1 backend E2E readiness

## Identity and source boundary

The demo product is **NexGen**, exposed as the **NexGen AI Retail Voice Commerce Assistant**. Runtime greetings, API descriptions, and voice responses use this identity.

The existing policy corpus is official Zara US reference material. The backend preserves `policy_source_brand=Zara`, `policy_market=US`, `policy_locale=en`, and `policy_usage=REFERENCE_DEMO`. NexGen does not claim that evidence as its own policy. Stable `zara-us:` catalogue IDs, source URLs, historical migrations, and source metadata remain unchanged because they preserve referential integrity and provenance. A client launch must replace the reference corpus and configure the client identity before policy answers are presented as client policy.

## Execution architecture

The request path is:

`VoiceService -> deterministic Orchestrator -> VoiceCapabilityExecutor -> LocalVoiceCapabilityBackend -> Policy RAG, RecommendationService, or ToolGatewayDispatcher -> domain services/repositories`

Voice code does not query Postgres. The dispatcher validates requests with the 30-tool registry schemas, calls existing domain services, normalizes results, and records sanitized audit entries. Policy questions use the existing hybrid RAG interface; product matching uses the existing MiniLM recommendation service; dynamic catalogue, inventory, customer, order, return, refund, rewards, promotion, and support facts use Tool Gateway services.

## Customer and session behavior

Sessions retain scoped authentication, active order/product/item/store references, shopping category and occasion, budget, size, fit, colors, materials, must/avoid preferences, location/deadline, secondary intents, and pending confirmation state. Raw transcripts are not persisted. A preference update adds or replaces the affected structured field while retaining other constraints.

Private tools require the existing scoped access token. Customer verification can place the issued token in server-side session state, while response metadata redacts tokens, confirmation material, verification proofs, email, phone, and destinations. Guest order scope and transaction customer scope continue to be enforced by `RetailCapabilityService`.

## Grounding and responses

The deterministic response composer returns concise speech without Markdown, raw JSON, URLs, internal tool names, or invented success. Policy answers use neutral reference-demo framing and abstain when evidence is insufficient. Recommendation speech uses at most three returned product records. Synthetic inventory, orders, loyalty, promotions, and support data retain their origin fields in structured metadata. Simple greetings, thanks, goodbye, and help are deterministic; unsupported general questions return `LLM_NOT_CONFIGURED`.

## Write safety

Cancellation, return, exchange, incident, and support-case writes use the existing preflight and HMAC confirmation flow. The adapter retains the gateway-issued confirmation token and generated idempotency key only in server-side session state. Only an exact affirmative confirms; negative replies clear the pending action; ambiguous replies remain at the confirmation boundary. Success is spoken only after the existing service completes its write and verification path.

## Evaluation coverage

`scripts/voice/evaluate_backend_e2e.py` covers greeting, FAQ, broad and faceted shopping, matching, product facts, size, inventory, pickup, authorized order history, demo rewards, promotions, tracking, cancellation preflight, return eligibility/preflight, exchange inventory/preflight, refund, damaged-item incident preflight, handoff, preference changes, multi-intent retention, unsupported general chat, insufficient evidence, unauthorized private access, and prompt injection.

The evaluator uses real backend services and real configured database fixtures through a connection wrapper that suppresses service commits. It rolls the transaction back at completion and never sends an affirmative write confirmation. This permits real reads, authorization, audit paths, and write preflights without persistent business-state mutation.

## Security reconciliation

The API keeps `X-Tool-Secret` dependencies. Existing RLS and database grants are unchanged. Confirmation HMAC, idempotency, scoped authorization, and domain rules are reused. Audit summaries exclude tokens, verification values, contact identifiers, destinations, and factual free text. Voice responses use generic errors and recursively redact sensitive structured metadata. Prompt-injection text requesting another customer’s records is refused before capability dispatch.

## Remaining integration work

Before Dokploy: set production secrets and allowed origins, configure health monitoring, run the full safe suite, run the rollback-safe E2E evaluator against the target database, and perform a local API smoke test.

Before Retell: add a provider adapter and verified webhook endpoint, map provider session IDs to voice sessions, configure call lifecycle and timeouts, and test audio interruption/error behavior. No Retell, telephony, STT/TTS, external LLM, Redis, or frontend integration is included here.

Production clients must replace or connect the policy corpus, catalogue source, identity provider, OMS, CRM, loyalty, promotions, messaging delivery, and human-transfer destination. These replacement points sit behind existing RAG, recommendation, and Tool Gateway service boundaries.
