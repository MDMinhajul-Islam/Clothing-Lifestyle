# Phase 2D security reconciliation

Scope: repository base `670d705`, existing Phase 2C gateway and additive Phase 2D knowledge layer. This is a code/configuration audit, not a penetration test. Existing gateway rules and security behavior were not redesigned.

| Severity | Finding and evidence | Implication | Recommended action |
|---|---|---|---|
| MEDIUM | Migration 006 creates public SELECT policies for `stores` and `inventory_levels`. | The handoff's blanket backend-only operational claim is incorrect. These records are synthetic. | Reconcile the documentation; decide whether direct shopping-client reads remain intended. AI access must still follow the gateway contract. |
| INFORMATIONAL | `backend/app/api/routes_meta.py` exposes GET `/v1/tools/definitions` without secret authentication. | Public discovery metadata is not an authenticated business operation; the handoff overstates endpoint protection. | Document the exception; review exposed schema descriptions for sensitive content. |
| HIGH | `backend/app/config.py` supplies development gateway/confirmation-secret defaults. | A deployment missing explicit secrets may accept known development credentials. Actual deployed values were not disclosed or audited. | Fail closed outside development and require independently configured secrets before production deployment. |
| HIGH | `OrderService.get_order` checks ownership only when `customer_verification` is supplied. | The shared gateway secret is not end-user authorization. | Establish authenticated customer context across account-specific tools in a separately scoped security change. |
| HIGH | `api/deps.py:log_tool_audit` catches persistence failures; mutations commit separately. | Successful changes can lack a durable audit trail. | Design transactional audit/outbox persistence and test failure paths. |
| HIGH | Routes pass payload dictionaries to `AuditRepository`, which serializes them without automatic redaction. | Confirmation tokens and customer identifiers may enter persistent request summaries; the handoff's automatic-redaction claim is unsupported. | Add an allowlisted audit projection, retention controls, and redaction tests in a dedicated change. |
| MEDIUM | Mutation idempotency keys are optional; HMAC tokens bind action/order/time, not the complete requested return payload. | The documented mandatory-idempotency and full-confirmation safety expectations exceed implementation. | Review required keys, payload binding and concurrent replay behavior separately. |

No CRITICAL finding was established within this bounded inspection. This does not certify production readiness.

## Phase 2D controls

- Knowledge tables have RLS enabled, no public policies, and explicit revocation from PUBLIC, anon and authenticated. Backend service-role ingestion is the only granted application write path.
- Migration/import verification checked RLS and role privileges on Supabase. Existing catalogue/operational rules were not changed.
- Knowledge contains public explanatory policy only. Customer data, live prices, inventory and operational statuses are excluded.
- Only official US English URLs are accepted. Captures are research-tool text extracts; no claim of direct HTTP success or independently verified upstream freshness is made.
- A direct public HTTP probe of HowToReturn received 403. No additional direct requests, private endpoints, challenge handling, cookies, identity spoofing or bypass techniques were used.
- The initial capture envelopes included a `direct_http_status` field propagated to all sources. Append-only access metadata corrects its scope: the 403 was observed only for HowToReturn, not separately for every page. Original captures remain unchanged.
- Raw extracts and normalized versions are immutable and hashed. Ingestion validates source/document/chunk relationships before writing.
- Retrieval SQL uses bound parameters, mandatory US/en filters, active versions and embedding provider/model/version/dimension filters. No SQL or credentials are exposed to an AI agent.
- The embedding adapter requires explicit configuration, rejects redirects and suppresses provider error bodies. No provider or model is selected by default; no embeddings were generated.
- Retrieval returns structured evidence or explicit insufficient-evidence/unavailable states, never an answer from model memory. No new public HTTP endpoint or LLM/voice integration was added.

## Validation boundary

Historical gateway integration tests were excluded because read endpoints also write audit records. Phase 2D import checks used a rollback transaction before the authorized additive live import. Retrieval evaluation used a read-only transaction. No production-like cancellation or return test was executed.
