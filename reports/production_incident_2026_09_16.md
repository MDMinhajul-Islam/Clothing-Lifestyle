# Production incident investigation — 2026-09-16

## Final handoff: user will deploy

The user has requested that further deployment be left to them. The local fix is ready; no further production mutations will be made. No commit or push has been made. The application was already Dockerized; the existing root Dockerfile is retained, with one build-time syntax check added.

The incident-only change is `production_incident_2026_09_16.patch`: extract the regex operation from the f-string for Python 3.11 compatibility, and compile backend source during the Docker build. All unrelated working-tree edits remain intact. There are no database, authentication, environment, Retell configuration, or API-contract changes.

**Deployment instructions:**

1. Restore responsive host/Dokploy access before starting another build. A successful SSH `uptime` returned load averages **30.32, 74.81, 80.66** on the two-core host. Subsequent diagnostics disconnected or timed out, so memory exhaustion, disk pressure and the exact process responsible remain unconfirmed. Do not start overlapping builds.
2. For the currently saved Dokploy overrides, use **Deploy**, not **Rebuild**. This installation's Deploy log confirmed `Applying 2 patch(es)...`; Rebuild bypassed the patches. Keep the existing environment and port 8000 configuration. Confirm the source revision is the intended one before deployment.
3. The saved overrides contain full files from commit `0653a4d86a5db91c45af105b317dd7f01325867b` plus only the incident fix. If deploying newer source, reconcile/remove these overrides first so they do not overwrite newer voice code. After manually accepting and committing the fix, remove the overrides when deploying that fixed source.
4. Confirm the build passes `python -m compileall -q backend`, the backend reaches **1/1 replicas**, and `/health` returns HTTP 200. A successful build/history badge alone is insufficient.
5. Verify populated product lists, search and product detail; existing-customer login and page-reload session restoration; voice greeting and a spoken product request reaching `nexgen_voice_turn`. Check browser console/network for failures. Do not run write-oriented order/refund tests against customer data.

**Validation completed:** 358 safe backend regression tests passed; 15 live gateway tests were deliberately excluded to prevent production writes. Frontend tests: 12 passed; production build passed. Actual Python 3.11 compiled all 97 backend files and passed five isolated email-correction cases. Full backend dependencies/tests ran under local Python 3.14, so this is not a claim that the full suite ran on Python 3.11. Detailed test outputs accompany this report.

**Outstanding:** successful patched production startup, container-to-database connectivity, live authentication/cookie restoration, and audible Retell conversation remain unverified. The historical cause of the missing image and the later host overload remain open. The code fix resolves the reproduced startup SyntaxError; it does not establish that the overloaded server has recovered.

> Current diagnosis: two confirmed backend-wide blockers — missing Docker image, then Python 3.11 import-time SyntaxError in `voice/service.py` exposed by image recovery. Correct Vite URL, CORS/portal settings, populated catalogue and auth tables have been verified. See the compatibility-fix section below. The minimal fix is implemented and tested locally and saved as two Dokploy patches. The patched Deploy confirmed both patches were applied, but final production verification is blocked by a subsequent server-level access failure. Production recovery is NOT yet claimed.

## Scope and evidence before changes

Investigated the deployed frontend and backend, source commit `0653a4d86a5db91c45af105b317dd7f01325867b`, Docker inventory and Swarm tasks in Dokploy, saved backend environment, the configured Supabase database using a read-only transaction, and Retell agent configuration through read-only REST requests. No application or deployment changes had been made when this initial report was written. Local pre-existing edits in `backend/app/voice/conversation_policy.py`, `backend/app/voice/service.py`, and `tests/test_voice_phase_2g1.py` belong to the user and are preserved.

Frontend: https://nexgenclothing-lifestyle-frontend-nexgen-d2dbf2-206-189-183-167.sslip.io

Backend: https://nexgenclothing-lifestyle-nexgenbackend-t-dab46e-206-189-183-167.sslip.io

## Confirmed common cause

The backend is not running despite Dokploy's successful deployment history and available Stop control. At approximately 02:42 UTC, Docker Swarm service `nexgenclothing-lifestyle-nexgenbackend-tok2fu` showed **0/1 replicas**. The latest five tasks were repeatedly **Rejected**, with the exact error:

`No such image: nexgenclothing-lifestyle-nexgenbackend-tok2fu:latest`

Dokploy Docker inventory contained the frontend container but no backend container. Both pages of Docker image inventory lacked the backend image. The configured backend domain routes HTTPS `/` to container port 8000, matching the Dockerfile's `0.0.0.0:8000` command. Public GET requests to `/health`, `/v1/catalogue/products?limit=1`, `/v1/catalogue/facets`, and `/v1/customer/auth/me` all returned **502 Bad Gateway**. A container cannot serve these routes while its image cannot be found.

The historical deployment used commit `0653a4d`; a read-only `git ls-remote origin refs/heads/main` returned that identical commit. Why the image disappeared is not yet established: deletion, cleanup, restoration of server state, and image-tag changes must not be stated as proven causes without audit evidence.

## 1. Products

- **Root cause/classification:** deployment/runtime image failure, followed by a confirmed Python 3.11 startup syntax error, prevents the backend catalogue endpoints from responding. Frontend error handling conceals the outage as an empty result.
- **Evidence:** gateway 502; Swarm 0/1 and missing-image error; storefront displays 0 products and “No matching pieces found.” The deployed JS bundle `/assets/index-9wZwwZpy.js` contains the correct HTTPS backend URL, so missing Vite build configuration is not the cause in this deployed asset. Browser console reports `[NexGen API] Direct health check failed: TypeError: Failed to fetch`.
- **Database evidence:** a read-only connection using local configured Supabase credentials returned 6,018 products and 38,002 variants. The saved deployment targets the same Supabase project. This proves database availability from this workstation, not from a nonexistent production container. No seeding or migration was performed.
- **Payload/UI path:** the browser does not receive a valid catalogue JSON payload. `App.tsx` catches the failure and assigns `localResults(filter)`; `FALLBACK_PRODUCTS` is an empty array. This is an error-display weakness, not proof that the database has no products.
- **Files:** `Dockerfile`, `frontend/src/lib/catalogueApi.ts`, `frontend/src/App.tsx`, `backend/app/api/routes_catalogue.py`, `backend/app/services/public_catalogue_service.py`, `backend/app/repositories/catalogue_repo.py`, `backend/app/db.py`.
- **Smallest safe fix:** restore the missing image and apply the isolated Python 3.11 syntax fix documented below, then let the existing service regain one healthy replica. Preserve existing catalogue, filters, response contracts, database and frontend bundle.
- **Risk/working features:** rebuilding consumes server resources and can fail if source-provider or dependency access has changed. Recovery should not alter application behavior; all backend-dependent features regain their existing implementation. Verify health and actual product responses after recovery. A UI error-state improvement is optional follow-up and not needed to restore data.

## 2. Silent voice assistant

- **Root cause/classification:** the same deployment failure blocks backend web-call authorization before the Retell SDK can receive an access token. The frontend's local fallback and timer make this appear like an active call.
- **Exact code path:** `startVoice` requests microphone access, then awaits `/v1/retell/create-web-call`, and only on success calls `RetellWebClient.startCall`. Failure enters `startFallbackVoice`; `createVoiceSession` creates a local ACTIVE session even after the backend request fails. The panel increments its timer whenever a session exists and state is not IDLE. Starting that fallback neither starts browser speech recognition automatically nor produces a greeting. Therefore timer progress is not WebSocket, microphone, audio playback, or Retell-call evidence.
- **Evidence boundary:** production backend is unreachable; source explains the reported timer/silence behavior. No live microphone call was started during this initial investigation, so a specific historical call's WebSocket/audio trace has not been captured. For a new browser call during this outage, conversation cannot reach Retell authorization, `nexgen_voice_turn`, or its function response.
- **Retell read-only check:** configured agent retrieval succeeds; latest retrieved version is 9 and marked unpublished. It has agent-first start and greeting `Hello.`. The `nexgen_voice_turn` tool points to the correct HTTPS `/v1/retell/function`, uses POST, `args_at_root=false`, speak-after enabled, speak-during disabled, and a 15-second timeout. Latest retrieved agent has no lifecycle webhook URL. These latest-version observations are not proof of which published version a historical call used. Missing lifecycle webhook does not itself explain failure to obtain call authorization or initial silence. No Retell settings were changed.
- **Files:** `frontend/src/App.tsx`, `frontend/src/lib/api.ts`, `frontend/src/components/voice/VoiceAssistantPanel.tsx`, `backend/app/api/routes_retell.py`, `backend/app/retell/client.py`, `backend/app/voice/providers/retell.py`, `docs/retell_custom_function_integration.md`.
- **Smallest safe fix:** restore backend availability first; the fully expanded saved environment already has the correct credentialed CORS origin. Verify create-web-call, SDK connection, greeting, signed function execution, and audible response before changing any Retell prompts, voice policies, or recommendation logic.
- **Risk/working features:** retaining the same source and Retell configuration avoids conversation regressions. In-memory sessions do not survive process replacement; the service currently has no running container. Actual audio and browser permissions require an end-to-end manual check after recovery.

## 3. Existing customer login

- **Root cause/classification:** backend unavailability (missing image, then Python 3.11 import failure) blocks authentication. The fully expanded saved deployment environment contains the correct explicit `CORS_ORIGINS`; the initial partial-editor suspicion was disproven before any change. Customer login/session restoration and Retell authorization both use `credentials: include`.
- **Evidence:** production `/v1/customer/auth/me` returns 502; frontend bundle points at the correct backend. Local reproduction of the default omitted-origin configuration returns wildcard origin without credential permission, but that default does not describe the saved production environment. Missing CORS headers on a proxy-generated 502 do not establish application CORS misconfiguration.
- **Authentication internals:** login looks up `customers JOIN customer_credentials`, verifies Argon2, checks verification/account/lock status, creates a random opaque session token, stores only its SHA-256 hash, and sends an HttpOnly cookie. It does not use JWT or Supabase Auth for portal passwords. Production cookie flags in the source are Secure, HttpOnly, SameSite=Lax, Path=/. Do not weaken these to work around a gateway or CORS problem.
- **Database evidence:** 2,003 customers, 3 credential rows, 7 session rows, 2 portal-token rows; all 3 password hashes are Argon2id, 2 verified, 0 currently locked. Migration 013's required tables exist. These aggregates cannot prove that every historical account exists or that a supplied password matches. No customer password was requested or tested; no account was reset.
- **Files:** `backend/app/config.py`, `backend/app/main.py`, `backend/app/api/routes_customer_auth.py`, `backend/app/services/customer_auth_service.py`, `backend/app/repositories/customer_auth_repo.py`, `supabase/migrations/013_customer_portal_auth.sql`, `frontend/src/lib/customerAuthApi.ts`.
- **Smallest safe fix:** restore backend image; preserve the already-correct `CORS_ORIGINS` and `CUSTOMER_PORTAL_URL`. Verify preflight, login, Set-Cookie, `/me`, reload restoration, logout, and ownership checks.
- **Risk/working features:** no CORS, cookie, password, or schema change is required. Preserve existing trusted origins, sessions, account status and ownership/security logic. A successful anonymous `/me` rejection is necessary but insufficient to establish a real customer login; manual login and restoration remain required.

## Correction after fully expanding the environment editor

The initial masked/virtualized Dokploy editor exposed only the first 23 lines. Opening the full editor revealed 56 lines and confirmed that `CORS_ORIGINS` already exactly matches the deployed frontend, `CUSTOMER_PORTAL_URL` is correct, the cookie is `nexgen_customer_session` with a seven-day lifetime, and SMTP variables are present. **The initial suspected missing-origin/portal configuration defect is ruled out.** No environment edit was made. The local default-CORS reproduction demonstrates a hypothetical default only, not the saved production configuration. Recovery is restricted to the missing image.

## Recovery plan and rollback

1. Preserve this evidence and the existing environment; do not change secrets or user code.
2. Restore the missing backend image from commit `0653a4d` using the existing Dockerfile and service. Do not blindly restart a service whose image is absent. Verify source selection before deployment.
3. Preserve all existing environment variables. Full-editor inspection confirms that the explicit frontend origin, portal URL, session configuration, and SMTP variables are already present.
4. Confirm Swarm 1/1, application startup/database/embedding warmup, `/health` 200, real catalogue payloads and search, expected authentication failures for anonymous requests, and correct CORS preflight.
5. Validate browser products and manual customer/voice flows. Do not make live orders, exchanges, refunds, or send SMTP messages as regression probes.
6. No commits or pushes. If a new image fails, preserve its logs and the original revision/config; do not rewrite business logic to mask a deployment failure. No environment rollback is needed because no environment change is required. No previous backend image is presently available for image rollback.

## Initial test results

- Frontend Vitest: **12/12 passed**, 3 files; duration 6.04s.
- Focused backend unittest: **149/149 passed**, 6.926s. Modules: customer auth, public catalogue, Retell transport, voice adapter, admin, email notifications, recommendations, backend capabilities, voice customer acceptance. These tests use local fakes/mocks, not production commerce writes.
- Read-only database checks: passed; transaction rolled back.
- Missing-origin CORS reproduction: confirmed the hypothetical default; full production-editor inspection ruled this out as the deployed configuration.
- Production HTTP smoke checks: **failed, 502** before recovery.
- Browser login, audible Retell conversation, and post-recovery production validation: pending.

## Reference documentation

- [Dokploy domain troubleshooting](https://docs.dokploy.com/docs/core/troubleshooting/domains): upstream port/listener troubleshooting. The configured port matches source in this incident; Swarm provides the stronger missing-image evidence.
- [Retell custom functions](https://docs.retellai.com/build/conversation-flow/custom-function): wrapped `name/call/args` payload when args-only is disabled.
- [Retell Get Voice Agent](https://docs.retellai.com/api-references/get-agent) and [Get Retell LLM](https://docs.retellai.com/api-references/get-retell-llm): read-only configuration inspection.

## Recovery execution and complete local regression

- At approximately 02:49 UTC, initiated Dokploy **Rebuild**, whose UI explicitly says it only rebuilds the application without downloading new code. No environment values were edited or saved. Source, secrets, routing, Retell settings and database are unchanged. Rebuild log confirms the existing Dockerfile and pinned CPU PyTorch dependency are being built.
- Full safe backend suite: **358 tests passed**, zero failures/errors/skips, 8.522 seconds. All 15 `TestToolGatewayAPI` cases were excluded because they persist audit/commerce data. `psycopg2.connect` and the application's live pool accessor were blocked for the whole suite. Local synthetic-data tests operate on fixtures/in-memory data, not production. Full per-test log: `reports/production_incident_2026_09_16_tests.txt`; machine-readable summary: `reports/production_incident_2026_09_16_tests.json`.
- These tests ran against the existing working tree including the user's three pre-existing edits, not a clean deployment checkout. The recovery rebuild uses server source, not these local edits.
- Frontend: all **12 tests passed**; `npm run build` passed TypeScript and Vite, transforming 1,887 modules. Existing bundle-size warning (>500 kB) remains; no optimization or redesign was attempted. The local build is validation only and was not deployed.
- Reproduction with the actual saved explicit CORS origin succeeds with exact `Access-Control-Allow-Origin` and `Access-Control-Allow-Credentials: true`. This further rules out the earlier partial-editor configuration hypothesis.

## Limits and recurrence prevention

- Dokploy Audit Logs shows an Enterprise-license gate on this installation, so this investigation cannot attribute the image disappearance to an actor, cleanup command, or exact time. The immediate runtime cause is proven; the historical deletion mechanism remains unknown.
- A rebuild of the same application source is not necessarily byte-identical: `python:3.11-slim`, OS packages, and transitive Python dependencies are not all locked to artifact digests. The missing original image prevents a binary comparison. Validate the freshly built runtime before calling recovery complete.
- Recommended follow-up after manual acceptance: retain versioned images in a registry and deploy by immutable digest; protect required images from cleanup; alert on backend `/health` and replica count rather than deployment history alone. These infrastructure changes are not silently included in this incident recovery.
- Retell microphone permissions, audio output device, real WebSocket connection and audible conversation cannot be certified by unit tests or an HTTP token response. Existing-account login cannot be certified from aggregate database counts. Those manual acceptance checks must be reported separately.

## Second confirmed blocker exposed by image recovery

The rebuilt image `sha256:a0ba38786ae86d5d98361104549991a48ec2bbbed68ab60e0e0c83257145e34f` built successfully, but service tasks then failed with exit code 1. Service logs at approximately 02:56 UTC identify `/app/backend/app/voice/service.py:994` in the deployed revision:

```text
return f"{re.sub(r'\d+$', replacement, local)}@{domain}"
SyntaxError: f-string expression part cannot include a backslash
```

`Dockerfile` uses Python 3.11. That Python version rejects a backslash inside an f-string expression. The local Python 3.14 test runtime accepts it, explaining why local tests passed while production could not import the app. Import chain: `main.py` → `routes_voice.py` → `voice/__init__.py` → `voice/service.py`; the syntax error prevents the entire API from starting, including catalogue and customer authentication. This is a **backend/runtime compatibility defect in addition to the missing deployment image**. Image recovery alone does not restore service. The disappearance mechanism of the original image is still unknown.

### Minimal compatibility patch

- In `_correct_pending_email`, evaluate the identical `re.sub` into `corrected_local`, then interpolate that variable. Pattern, inputs, output, control flow and email semantics remain unchanged. This is one replaced line plus one new line; the user's unrelated edits in the same file remain intact.
- Add `RUN python -m compileall -q backend` after the Dockerfile source copy so the actual image interpreter catches syntax failures during build instead of accepting an image that immediately crashes. No runtime upgrade or dependency change.
- Regression risk is low: only expression placement changes. Validate exact production-version parsing and existing voice/email-correction tests.
- No commit or push. A Dokploy build patch can apply this same isolated change to the server's existing source for manual production acceptance without including local uncommitted work. Such patches are persistent and must be removed after the corresponding source fix is eventually approved and deployed, to avoid overriding future source changes.

Reference: [Dokploy Patches](https://docs.dokploy.com/docs/core/patches) documents build-time file overrides without modifying the source repository.

### Compatibility validation after the minimal code fix

- Downloaded the official Python 3.11.9 Windows embeddable runtime into ignored `tmp/production-python311` for interpreter-specific validation.
- The unmodified Git HEAD version fails compilation on Python 3.11 at line 994 with the exact production SyntaxError.
- All **97 backend Python files** compile with the fixed source on Python 3.11.
- Five isolated email-correction behavior cases pass on Python 3.11 (spoken replacement, numeric replacement, unrelated speech, no numeric suffix, malformed address).
- Re-ran the complete safe regression suite after editing: **358/358 passed**, zero failures/errors/skips; live DB blocked, 15 live gateway tests excluded. See `production_incident_2026_09_16_postfix_tests.txt` and `.json`. Full suite uses the installed Python 3.14 dependencies; Python 3.11 checks cover all backend syntax and the affected function, with the production build/import providing the next runtime gate.
- Dokploy editor verification confirms the voice patch differs from the server's full original file only by the intended expression extraction. The Dockerfile patch only adds the build-time compile check. Neither patch copies the user's local uncommitted conversation changes.

### Deployment workflow correction

Both Dokploy patches were saved and confirmed enabled. A second **Rebuild** showed the original eight Dockerfile stages and no syntax gate, proving that this installed version's rebuild path does not apply the saved patches. That unpatched build was explicitly stopped. The configured repository's `main` was checked directly again and still resolved to `0653a4d86a5db91c45af105b317dd7f01325867b`. A **Deploy** was then initiated to run the clone-and-patch workflow. No Git commit, push, environment edit, runtime-version upgrade, schema change, or credential change was made.

Python reference: [Python 3.12 f-string changes](https://docs.python.org/3.12/whatsnew/3.12.html#pep-701-syntactic-formalization-of-f-strings) documents that backslashes in expression parts were prohibited before Python 3.12. The actual failure and fixed parsing were also reproduced on Python 3.11, so this conclusion does not rely on documentation alone.

## Latest deployment/access status after interruption

The manual Deploy log explicitly showed `Applying 2 patch(es)...` and a nine-stage Dockerfile (rather than eight), confirming that this workflow applies both saved overrides. The latest observed log reached installation of the CPU PyTorch dependency. No successful compile-gate completion, healthy replica, or HTTP recovery has yet been observed for that patched image.

After the interrupted wait, fresh independent probes found:

- Dokploy `http://206.189.183.167:3000`: connection refused.
- Backend HTTPS: TLS handshake timeout.
- Frontend HTTPS: TLS handshake timeout.
- TCP ports 80 and 443 accept connections; TCP port 22 accepts a connection but does not return an SSH banner within five seconds; port 3000 refuses the connection.
- The existing browser tab still renders previously captured deployment logs. Cached UI is not evidence of current server health.

This is broader than the original backend-only 502 incident. Resource pressure during builds, host/container failure, and networking remain hypotheses; no kernel, memory, disk, or provider-console evidence is available yet to distinguish them. No server-wide restart, image cleanup, or unrelated-application change was attempted. Existing SSH/provider-console access has been requested.

The synthetic acceptance account from migration 013 was separately checked in a read-only transaction: it exists, is ACTIVE and verified, and its stored Argon2 hash verifies against its known test password. No customer credentials were changed, no login attempts were sent to production, and no session or commerce rows were written by this check. This narrows credential-storage concerns but does not replace browser login/session acceptance.

### Reviewable deliverables and remaining acceptance

- `reports/production_incident_2026_09_16.patch` contains only this incident's two file changes relative to HEAD. It deliberately excludes all pre-existing user edits.
- Local compatibility fix: `backend/app/voice/service.py` (current working-tree lines 1003–1004).
- Build gate: `Dockerfile` (`RUN python -m compileall -q backend`).
- Saved, enabled Dokploy overrides: `backend/app/voice/service.py`, `Dockerfile`. These persist across Deploy actions. Once the corresponding source changes are manually accepted, committed by authorization, and deployed, remove those overrides so future source updates are not masked.
- No commit or push has been made.
- Pending: restore server management access; inspect host memory/disk/kernel and build status; finish the patched deployment; verify one healthy replica and `/health` 200; verify catalogue, search, details, CORS, synthetic browser login/logout and restoration, real customer manual login, Retell call authorization, SDK/audio and signed function response.
- Existing local test results are valid but do not certify those pending production checks. Do not label the incident resolved until these pass.
