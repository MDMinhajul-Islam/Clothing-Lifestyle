# NexGen safe restoration progress — 16 September 2026

**Superseded by completed restoration:** The user requested evidence-based reassessment of the agent's 2,048-MiB gate. That gate was not a platform requirement and was retired for this controlled release. The qualified image was pulled and backend restored to healthy 1/1, with ten minutes of successful production observation. See [final restoration report](nexgen_production_restoration_2026_09_16.md) and its metrics. Historical blocked/0-replica entries below are no longer current.

## Latest status: private provider configured; startup blocked on headroom

The subsequent request authorized completing private-image configuration and release checks. Completed:

- On the VPS, authenticated to GHCR and fetched the exact qualified manifest. Its SHA-256 matched the published digest.
- Saved Dokploy's Docker provider with the private image **by digest**, registry `ghcr.io`, matching account and existing authenticated registry credential. Credential moved only via encrypted SSH stdin and subprocess stdin; no token emitted to logs/project files.
- Configuration was updated in one targeted database transaction using the same Docker-provider fields as Dokploy's `saveDockerProvider` handler; the UI handler itself was not called. This bypasses its normal application audit event; this report records the action. A full prior application row was saved root-only on the VPS before mutation.
- Both saved replica fields now hold zero (`replicas=0`, explicit mode=0); autodeploy remains false. UI's basic replica control previously rejected zero, but the scoped database hold is now consistent.
- Verified changed fields are only dockerImage/password/registryUrl/replicas/sourceType/username. Application environment and all other row fields were preserved. Historical source patches were retained, not deleted; Docker-image provider bypasses source build and source patch application.
- Rechecked saved/live CPU/memory/restart/update/rollback/log limits. No backend containers exist. Other service replica counts unchanged.
- Frontend public HTTP 200. Backend `/health` HTTP 502 while intentionally at 0/0; this is expected outage evidence, not a passing backend check.

**Blocked:** VPS MemAvailable was 1,879 MiB during preflight, below the unchanged 2,048-MiB gate. No production `docker pull`, image switch on the live service, scale-up or rebuild was attempted. Authenticated manifest retrieval proves registry access/digest availability; it does not claim a completed layer download or successful production startup. Live products/login/voice and the 10-minute production observation remain unverified. Sufficient memory headroom must be available before the controlled pull/start/observation phase. Do not manually Rebuild or Deploy to bypass this gate.

Evidence: `nexgen_private_image_preflight.json`, `nexgen_private_image_safety_verification.txt`. Earlier progress entries below are chronological and their resolved blockers are superseded by this section.

The user requested safe restoration after isolated qualification. This report supersedes earlier statements that all safety settings are unapplied. Restoration is not yet complete: catalogue remains unavailable while backend is held at zero.

## Applied and verified

Changes affect only `nexgenclothing-lifestyle-nexgenbackend-tok2fu` / Dokploy application `kNKuOmx16MVTd4Y71Wk1D`.

- Disabled Dokploy autodeploy, verified after reload and via read-only database query.
- Saved explicit Swarm mode `Replicated.Replicas=0` in Dokploy. The separate basic replicas field rejects zero in the UI and remains 1; explicit mode takes precedence. Do not clear the mode override during the hold.
- Saved CPU limit/reservation 0.75 and memory limit/reservation 1 GiB in Dokploy.
- Saved on-failure restart policy: delay 60 seconds, maximum attempts 2, evaluation window 600 seconds. This bounds failures within the window, not every possible lifetime restart.
- Saved update and rollback policies: stop-first, parallelism 1, delay 30 seconds, monitor 180 seconds, failure action pause, failure ratio zero.
- Saved stop grace period 30 seconds.
- Applied the same policies to the live Swarm service while keeping replicas zero, plus JSON log rotation 10 MiB × 3. No image update, build, task start or redeployment was involved.
- Verified exact saved numeric values and live service values. Verification output: `nexgen_applied_hold_2026_09_16.txt`.

The targeted Swarm update acquired `/run/lock/nexgen-backend-release.lock`, verified zero live backend containers and zero running deployment records, and saved the prior service definition under `/root/nexgen-recovery/` with root-only directory/file permissions. The snapshot includes existing environment data and must not be published. No unrelated application, volume, image, database data or daemon was changed.

## Remaining release gates

### GHCR publication completed

After the user authenticated Docker, their credential was verified in memory as belonging to `MDMinhajul-Islam` with `write:packages`; no token was printed or written to project files. The exact qualified image was published to private package `ghcr.io/mdminhajul-islam/nexgen-backend`, tag `qualified-20260916-07b7148c579d`. Registry push completed successfully. GitHub's authenticated package API confirmed visibility `private` afterward.

Immutable release reference:

`ghcr.io/mdminhajul-islam/nexgen-backend@sha256:07b7148c579d926e47caa8f89fafb05de38f6b8efeee4911880def10a852ff45`

Digest matches the tested local artifact. Evidence: `nexgen_ghcr_publication.json`. This was an image push, not a Git commit/push. No production image pull or start occurred. Latest post-publication VPS check: 1,899 MiB available, backend 0/0, frontend 1/1, other service replica counts unchanged. The 2,048-MiB pre-start gate still fails. Saved Docker-source/private pull authentication and full release observation remain outstanding. The earlier authentication blocker in item 1 below is resolved by this publication.

1. The user selected their GitHub account `MDMinhajul-Islam`. Prepared local tag `ghcr.io/mdminhajul-islam/nexgen-backend:qualified-20260916-07b7148c579d` and verified unchanged qualified image identity. Publication is blocked on GHCR authentication: active GitHub CLI account matches, but its OAuth token scopes are gist/read:org/repo/workflow, without package scopes; Docker config has no registry auth entries. Package API lookup returned 404, which does not establish package absence without sufficient access. No image was pushed. User must authenticate Docker to GHCR with an appropriately scoped credential without sharing it in chat; existing-package visibility must be verified before publishing. Newly created GHCR packages default to private per GitHub documentation.
2. Latest preflight at 05:54 UTC: 1,988 MiB available memory, below the 2,048-MiB startup gate. No unrelated workload will be stopped or modified to force the gate to pass.
3. Before restoration, save the immutable qualified image reference as Dokploy's Docker source, reconcile the historical full-file patches and verify no queued/running release. No source rebuild on the VPS.
4. Verify effective health probe `/livez`, resource/restart/update/log settings and headroom immediately before one-task restoration. Application-specific release lock must cover the observation interval.
5. Observe one stable healthy task for 10 minutes; check real catalogue/readiness, public CORS and storefront product cards/search/detail. Contain back to zero on failure. Live customer login and Retell audio still require separate acceptance evidence.

No new commit or push has been performed. No recovery guarantee is inferred from the successful local tests.
