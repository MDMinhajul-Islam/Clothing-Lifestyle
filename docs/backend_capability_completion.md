# Phase 2F.1 backend capability completion

## Capability architecture

Phase 2F.1 adds a strict-schema retail capability service over existing repositories, domain services, confirmation HMACs, idempotency records, and Tool Gateway audit logging. New private operations require an expiring opaque access token whose SHA-256 hash alone is stored. The access levels are `PUBLIC`, `ORDER_VERIFIED`, and `TRANSACTION_VERIFIED`.

Registered shoppers verify an exact email or phone identifier using a matching synthetic address postal code. Guest purchasers verify an exact synthetic order number using its customer email and receive access to that order only. Identification returns masked data and never returns a profile. The deterministic orchestrator now selects the secured profile/history tools rather than the legacy `get_customer` lookup.

## Added tools

The gateway expands from 16 to 30 tools with `get_size_guidance`, `check_pickup_availability`, `identify_customer`, `verify_customer`, `get_customer_profile`, `get_customer_orders`, `get_loyalty_status`, `check_promotion`, `check_exchange_inventory`, `create_exchange`, `create_incident`, `create_support_case`, `prepare_handoff`, and `send_secure_link`.

`check_exchange_inventory` is the authenticated Phase 2F.1 alias for the existing `check_exchange_availability` behavior. The existing `get_customer` name remains registered for backward compatibility behind the application-level gateway secret, while orchestrated customer profile access uses `get_customer_profile` and requires transaction verification. Existing `find_stores` and `track_order` are the handbook equivalents of nearby-store search and shipment status.

## Database and synthetic provenance

Migration 010 creates private `customer_auth_sessions`, `loyalty_accounts`, `promotions`, `incidents`, and `support_cases` tables with foreign keys, RLS, and service-role-only grants. A separate deterministic seed populates one synthetic loyalty account per synthetic customer and three clearly synthetic promotion examples. Existing `exchanges`, `tool_idempotency_keys`, and `tool_audit_log` tables are reused.

Pickup, loyalty, promotion, exchange, incident, support, and link outputs retain `synthetic_operational_layer` provenance. Promotion eligibility and pickup state are computed by backend rules. Secure-link dispatch always reports `DELIVERY_NOT_CONFIGURED` and never claims delivery.

## Write safety

`create_exchange`, `create_incident`, and `create_support_case` use the existing signed confirmation-token functions and idempotency repository. Exchange creation performs eligibility and inventory checks before confirmation, writes the existing return/exchange model, and reads the exchange back before reporting success. Gateway routes sanitize access tokens, confirmation tokens, verification proofs, destinations, and factual summaries from audit payloads.

Phase 2G files remain intact. Only voice session context, clarification prompts, continuation messages, and generic confirmation wording were extended for the new tools. No Retell, LiveKit, telephony, or external LLM integration is included.

## Current limitations

Authentication is a secure synthetic demo mechanism rather than an enterprise identity provider. Auth sessions have no automated cleanup job. Existing legacy private tools retain their prior application-secret contract for backward compatibility; orchestrated flows use the new customer-scoped tools. Missing-item intake records the verified claim but does not adjudicate fraud or disputes. Messaging, checkout, and telephony dispatch remain unconfigured.

## Manual VS Code PowerShell runbook

Run from `F:\NEXVIX INTERN\Clothing Lifestyle` and stop at the first failure.

```powershell
python -c "from backend.app.config import settings; print({'SUPABASE_DB_URL_configured':bool(settings.supabase_db_url)})"
python -m scripts.backend_capabilities.manage_phase_2f1 --apply-migration
python -m scripts.backend_capabilities.manage_phase_2f1 --seed
python -m scripts.backend_capabilities.manage_phase_2f1 --verify
python -m unittest tests.test_backend_capabilities -v
python -m unittest tests.test_orchestrator -v
python -m unittest tests.test_voice -v
python -m scripts.voice.demo_voice_flow
python -m scripts.zara_knowledge.run_safe_tests
git status --short
$phase2dReportStatus = git status --short -- docs/phase_2d_test_report.json
if ($phase2dReportStatus) { git restore -- docs/phase_2d_test_report.json }
git diff --check
git diff --stat
git add backend/app/api/routes_tools.py backend/app/api/routes_voice.py backend/app/main.py backend/app/orchestrator backend/app/repositories/capability_repo.py backend/app/schemas/capabilities.py backend/app/services/capability_service.py backend/app/tools/definitions.json backend/app/tools/registry.py backend/app/voice docs/ai_orchestrator.md docs/backend_capability_completion.md docs/voice_agent_integration.md scripts/backend_capabilities scripts/voice supabase/migrations/010_retail_capabilities.sql tests/test_backend_capabilities.py tests/test_voice.py
git commit -m "feat(backend): complete retail customer and support capabilities"
git push origin main
git status --short --branch
```

Expected results: DB configuration is true; migration and seed report `APPLIED`; verification reports three promotions, loyalty count equal to synthetic customer count, zero invalid provenance, and zero orphans; focused suites and the safe suite report `OK`; the final Git state is clean and synchronized. Send the failed command, traceback or SQLSTATE, reported counts, and last 50 lines for any failure. Never send database URLs, access tokens, verification proofs, or confirmation tokens.
