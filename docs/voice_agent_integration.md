# Phase 2G provider-neutral voice integration

## Architecture and boundaries

The voice layer normalizes transcript events, maintains short-lived conversation state, asks the deterministic Phase 2F orchestrator for a structured plan, and passes that plan to a capability executor. It contains no SQL, database credentials, STT, TTS, external LLM, or provider SDK.

The capability executor is an interface boundary. Its local default calls the existing official policy RAG interface. Tool Gateway and Phase 2E recommendation execution remain adapter-driven so the voice layer does not duplicate gateway dispatch or access Postgres. Focused tests use a fake adapter, and the demo labels all policy and business results as stubs.

Provider mapping is: provider event → `VoiceTurnRequest` → `VoiceService` → `VoiceTurnResponse` → provider response. `MockVoiceProviderAdapter` implements this contract locally. A future Retell or LiveKit adapter can normalize and format provider payloads without changing session, orchestration, or confirmation logic.

## Sessions and turn processing

`InMemoryVoiceSessionStore` provides thread-safe create, get, update, and end operations. State includes customer/order/product context, last route and intent, missing-context continuation, pending write arguments, a gateway-issued confirmation token, and turn count. Raw transcripts are not stored.

Each turn merges explicit incoming context with retained context, routes through the orchestrator, asks deterministic clarification questions for missing fields, and executes only through the injected capability boundary. Explicit IDs can be retained across turns. Production must replace this process-local store with Redis or another distributed store with expiration and appropriate encryption/access controls.

## Confirmation flow

For `cancel_order` and `create_return`, the voice service calls `prepare_write`, which represents the existing non-mutating Tool Gateway preflight. The gateway must validate eligibility and issue its signed confirmation token. Voice stores that token temporarily and asks the caller for explicit confirmation. A later yes calls `confirm_write` with the same token and arguments; voice neither creates nor validates tokens. No clears pending state without calling the gateway. If no token is available, confirmation safely stops.

## Responses and safety

Responses carry concise `spoken_text` plus route, intent, tool, execution status, missing fields, and structured capability metadata. Policy insufficiency uses the existing abstention meaning. Recommendation summaries use only returned product names. Price, inventory, variants, and availability remain downstream authoritative data; synthetic inventory provenance remains in capability metadata.

All voice endpoints reuse `X-Tool-Secret`. Exceptions are sanitized, secrets are never logged, and transcripts/customer records are not logged or persisted by the voice layer. The current mock provider performs no webhook authentication because it is local-only; real adapters must implement provider signature validation.

## Local endpoints

- `POST /v1/voice/session`
- `POST /v1/voice/turn`
- `DELETE /v1/voice/session/{session_id}`

Only provider `mock` is currently accepted. General chat returns `LLM_NOT_CONFIGURED`, with a deterministic greeting/help response. No external conversation model is called.

## Manual VS Code PowerShell runbook

Run from `F:\NEXVIX INTERN\Clothing Lifestyle` and stop at the first failure.

```powershell
python -m unittest tests.test_voice -v
python -m scripts.voice.demo_voice_flow
python -m scripts.zara_knowledge.run_safe_tests
git status --short
git diff --check
git diff --stat
git restore docs/phase_2d_test_report.json
git add backend/app/api/routes_voice.py backend/app/main.py backend/app/voice docs/voice_agent_integration.md scripts/voice tests/test_voice.py
git commit -m "feat(voice): add provider-neutral voice agent integration"
git push origin main
git status --short --branch
```

Expected: focused tests pass; the demo clearly labels stubbed outputs and declines the pending cancellation; the safe suite reports `OK`; the final status is clean and synchronized. If `git restore docs/phase_2d_test_report.json` reports that the path did not change, continue. On any other failure, send the failed command, failed test names or traceback, and the last 50 lines.
