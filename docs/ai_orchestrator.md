# Phase 2F deterministic AI orchestrator

The orchestrator is a pure routing layer. It never opens a database connection and never executes a tool. `POST /v1/orchestrator/route` uses the existing `X-Tool-Secret` authentication dependency and returns a structured route, intent, confidence, context status, tool arguments, and short reason codes.

Priority is fixed: explicit writes, dynamic account/order/inventory facts, official Zara US policy, reference-based product recommendation, then general chat. Write confirmation flags come from the existing Tool Gateway registry; confirmation tokens remain entirely in the gateway.

`POLICY_RAG` plans target `retrieve_policy_knowledge`, which preserves official-source filtering and insufficient-evidence behavior. `PRODUCT_RECOMMENDATION` selects the registered `find_similar_products` or `recommend_matching_products` tools. Exact attribute/category browsing such as “Show me black dresses” routes to `TOOL_GATEWAY/search_products`; reference-relative language such as “similar to this” or “matches this shirt” routes to product recommendation.

Explicit IDs may be copied from the message or structured context. Required IDs are never guessed. Missing requirements return `NEEDS_CONTEXT` with `missing_fields`. The router exposes no chain-of-thought and adds no model or paid API dependency.

## Manual VS Code PowerShell runbook

Run from `F:\NEXVIX INTERN\Clothing Lifestyle` and stop at the first failure.

```powershell
python -m unittest tests.test_orchestrator -v
```

Expected: 12 tests pass. On failure, send the failed test names and traceback.

No separate demo script was added; focused tests exercise the offline route decisions without database access.

```powershell
python -m scripts.zara_knowledge.run_safe_tests
```

Expected: the established safe suite plus Phase 2F tests reports `OK`. On failure, send failed test names and the last 50 lines.

```powershell
git status --short
git diff --check
git diff --stat
```

Expected: only Phase 2F files are changed and `git diff --check` has no substantive errors.

```powershell
git add backend/app/api/routes_orchestrator.py backend/app/main.py backend/app/orchestrator docs/ai_orchestrator.md tests/test_orchestrator.py
git commit -m "feat(orchestrator): add deterministic AI request routing"
git push origin main
```

Expected: Phase 2F is committed and pushed. On Git failure, send the complete command output and `git status --short`.
