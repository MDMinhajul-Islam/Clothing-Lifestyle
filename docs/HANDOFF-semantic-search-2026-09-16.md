# NexGen handoff — semantic product search

## User request and immediate state

User wants the AI shopping assistant to recommend real related catalogue products
when exact wording does not match inventory names. This must apply to all product
searches, not only office dresses, and must preserve other business logic. User
requested an immediate stop and detailed handoff due to token limits.

Implementation is LOCAL ONLY. No commit, push, build or deployment was performed
for this semantic-search change. Production was already restored before this work.
Do not tell the user this fix is live.

Workspace: `F:\NEXVIX INTERN\Clothing Lifestyle`, PowerShell.
Branch: `codex/production-recovery`.
Last known HEAD/pushed recovery commit:
`240e2de935e4d90016ffbb917af950f80d577459`.
Remote: `https://github.com/MDMinhajul-Islam/Clothing-Lifestyle.git`.
Verify git status before doing anything; do not stage all files.

## Production context — preserve the recovered service

VPS: `206.189.183.167`, Ubuntu 24.04, Docker/Dokploy, ~3.8 GiB RAM, no swap.
Prior rebuild incident produced five same-slot backend tasks, extreme CPU/load
and memory pressure. Do not rebuild on this VPS, prune, delete volumes, restart
Docker, or change unrelated deployments.

Recovered backend service: `nexgenclothing-lifestyle-nexgenbackend-tok2fu`.
Dokploy backend app ID: `kNKuOmx16MVTd4Y71Wk1D`.
Qualified image currently deployed:
`ghcr.io/mdminhajul-islam/nexgen-backend@sha256:07b7148c579d926e47caa8f89fafb05de38f6b8efeee4911880def10a852ff45`.

Last verified configuration: one healthy replica, 1 GiB memory limit/reservation,
0.75 CPU limit/reservation, stop-first update/rollback, parallelism 1, delay 30s,
monitor 180s, failure action pause; restart on-failure, delay 60s, max attempts 2,
window 600s. Backend auto-deploy disabled. Private GHCR pull configured.

Frontend was deliberately untouched and its main-branch auto-deploy was still
enabled. A push to main can trigger an unwanted frontend build. Earlier recovery
commit was pushed to the separate recovery branch. Do not merge/push main casually.

Prior restoration observation passed 10 minutes after readiness: startup ~34s,
zero restart/OOM, steady cgroup memory ~721 MiB, peak ~808 MiB including auth test,
host available RAM >=1466 MiB after readiness, final load ~0.51. Catalogue returned
5905 products. User confirmed the website was working. These are historical
measurements, not fresh checks from this turn. A 2048 MiB free-RAM gate was an
unnecessary agent heuristic and has been retired; do not reintroduce it.

Backend URL:
`https://nexgenclothing-lifestyle-nexgenbackend-t-dab46e-206-189-183-167.sslip.io`
Frontend URL:
`https://nexgenclothing-lifestyle-frontend-nexgen-d2dbf2-206-189-183-167.sslip.io`

See `docs/production-recovery.md` and
`reports/nexgen_production_restoration_2026_09_16.md` for restoration evidence.
Ignored helpers in `tmp/` include `nexgen_verify_hold.py`,
`nexgen_controlled_restore.py`, `nexgen_live_smoke.py`. Read before use; do not
rerun mutation/recovery scripts automatically. Credentials/env snapshots must
never be printed, committed or included in reports.

## Reproduced problem

Real Retell main-site call, agent Clothing_Lifestyle v9, Sept 16 12:42 +06:
user intended office dress, ASR produced "formal raise for my office". Search
returned no office pieces and asked about color/budget that user never supplied.
"Please try" then returned generic chat with `LLM_NOT_CONFIGURED`.

Code evidence:
- CatalogueRepository.search_products applied full-text matching as a mandatory
  WHERE condition. Vector distance only ordered survivors; semantic matches with
  different words could never be candidates.
- Existing relaxation required recognized type/category, leaving unknown names
  without vector recovery. Occasion fallback retained the failed lexical query.
- Filler words such as im/buy/is/there/any/available/products survived parsing.
- VoiceService did not recognize "Please try" as search continuation.

## Local implementation completed

1. `backend/app/repositories/catalogue_repo.py`
   Added optional `semantic_only=False` argument. When enabled, clears lexical
   query, requires ACTIVE lifecycle and matching stored embedding identity,
   similarity >=0.30, then uses existing cosine-distance ordering. Other facets
   remain in SQL. No vector returns empty, not random catalogue. Count/select
   share candidate conditions. Default exact search remains unchanged.
2. `backend/app/services/catalogue_service.py`
   Empty exact searches can use semantic candidates even without recognized type.
   Occasion fallback uses the original utterance vector without literal occasion
   or keyword gating. Keeps department, category/id, product type, color, size,
   material, brand, min/max price, sale and limit. Adds conversational fillers.
   Honest alternative/empty messages replace ungrounded styling claims and the
   hardcoded color/budget question. Existing composer speaks up to three real
   result names/prices; it was not changed.
3. `backend/app/voice/service.py`
   Recognizes exact short retries: please try / try again / please try again.
   Retries preserve constraints instead of invoking automatic broadening.
4. `tests/test_search_quality.py`
   Updated one expected fallback path from 3 queries to 2 with semantic mode.
5. NEW `tests/test_semantic_search_recovery.py`
   Nine regression tests covering unknown names, strict facets, empty/no-vector
   results, fillers, SQL filters/parameter counts, preserved exact behavior and
   multi-turn voice retry through routing/execution.

Pre-existing uncommitted changes were intentionally PRESERVED:
- `backend/app/voice/conversation_policy.py`: guarded office desk -> dress ASR clarification.
- `backend/app/voice/service.py`: related preference/ASR context changes alongside
  the new retry patch; inspect diff carefully to distinguish.
- `tests/test_voice_phase_2g1.py`: pre-existing tests for those changes.
These were excluded from the previously qualified production image and recovery
commit. Do not discard them or imply they were deployed.

Many unrelated untracked deployment reports/proposals remain. In particular,
`deploy/nexgen-backend-safety.json` may describe the obsolete zero-replica hold
and 2048 MiB gate; it is not the current effective production configuration.

## Validation results and limits

- New semantic suite: 9/9 PASS.
- Existing search-quality suite: 11/11 PASS.
- Existing `test_voice*.py` suites: 133/133 PASS.
- Broad offline run: 369 attempted, 360 PASS, 9 ERROR, no assertion failures.
  Errors were Windows temporary-directory permission failures in
  `test_rag.TestPolicyRag.test_immutable_capture` and eight
  `test_throughput_optimization.TestThroughputOptimizationComprehensive` tests.
  Two additional exact-search tests were added after this run and passed in the
  final nine-test targeted suite. Suite totals overlap.
- Broad runner excluded 15 live TestToolGatewayAPI tests; psycopg2.connect was
  patched to raise to prohibit live database access. Authentication, security,
  recommendations, Retell, orchestration and commerce offline tests passed.
- Production Python 3.11 AST parse and git diff --check PASS.
- Broad output: ignored `tmp/semantic-regression-results.txt`.

Commands:
```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_semantic_search_recovery.py -v
.venv\Scripts\python.exe -m unittest discover -s tests -p test_search_quality.py -v
.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_voice*.py'
```
The existing broad runner is `tmp/run_safe_no_report.py`; it does not block DB
access itself. The last run wrapped it with a mock of psycopg2.connect before
discovery. Do not run live gateway tests against production.

## Next agent: concrete remaining work

1. Review the local diff and this report; do not redo recovery or rebuild.
2. Validate semantic SQL and ranking on an isolated/read-only catalogue with real
   stored embeddings. Current tests mock vectors/DB; they do NOT prove actual
   retrieval relevance, coverage, query plans or latency. Check synonym phrases
   across shoes, bags, outerwear, dresses and broad occasion requests, plus exact
   queries and incompatible strict filters. Test the reported call wording.
3. Review similarity floor 0.30. It follows the existing policy-RAG convention,
   not product-specific calibration. Do not claim it guarantees relevance.
   Measure fallback query cost; it adds DB work only after an exact miss and
   reuses the one query embedding. Review active/embedding coverage and any
   product-type name regex restrictions against actual catalogue aliases.
4. Resolve the nine temp-directory errors using an appropriate local test
   environment, without editing application behavior merely to pass tests.
5. If further edits are necessary, keep them narrowly scoped and rerun affected
   tests. Preserve explicit constraints and avoid invented availability claims.
6. Report local qualification separately from deployment. User's earlier push
   approval applied to recovery; no new voice-fix push/deployment occurred here.
   Confirm current desired release scope before external publication. Never
   silently trigger main-branch frontend auto-deploy.
7. Only after qualification and authorized release, build off the constrained
   VPS, use a pinned qualified image, restore only backend and monitor with the
   existing guarded process. Existing production image must remain rollback-safe.

More focused change report:
`reports/semantic_search_recovery_2026_09_16.md`.
