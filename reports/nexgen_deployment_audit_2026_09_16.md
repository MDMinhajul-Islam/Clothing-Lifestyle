# NexGen deployment incident audit — 2026-09-16

## Decision and preserved safety state

**Not approved for rebuild or production restoration yet.** This audit used read-only SSH, Docker inspection, retained journal/build logs, and read-only SELECT transactions against Dokploy's configuration database. No production data, service configuration, image, container, network, volume, or unrelated project was changed. No Docker restart, image build, deployment, image pull, or production test container was initiated. Local patch files and offline tests were prepared only; they have not been committed or pushed.

Verified live at 05:04–05:11 UTC: NexGen backend `0/0`, zero retained backend containers/tasks; frontend `1/1`; the other listed active Swarm applications and Dokploy/PostgreSQL `1/1`. Some unrelated services were already `0/0` and were left untouched. Initial recovered memory: 2,057 MiB available out of 3,915 MiB, no swap. Later interval samples showed 94–97% CPU idle. Long-window load averages were still decaying. Replica state does not certify every unrelated application's business functions.

**Outstanding hazard:** Dokploy's application record still stores replicas **1**, `autoDeploy=true`, and no safety overrides, even though the live service is manually scaled to zero. Another deployment could reactivate it. This was reported, not silently changed.

Final read-only check at **05:17 UTC**: backend remains zero with no containers; other listed previously active Swarm services remain 1/1. Load **0.31 / 2.12 / 24.79**, available memory **1,984 MiB**. This later headroom is below the proposed conservative 2,048 MiB admission gate, so it does not authorize even the proposed single-instance production trial. No need to alter the recovered host merely to satisfy the gate; qualify off-host and reassess its workload/headroom before restoration.

## A. Confirmed causes and evidence limits

The incident is a deployment-containment failure: a failing backend was left under unlimited, fast task replacement, start-first update/rollback and no resource limits on the same small host as its orchestrator and other production applications. The successful patched image build did not establish a healthy service. Resource saturation progressed to global OOM events, manager heartbeat failures, health-check execution failures and unresponsive Docker operations. Five distinct generations of NexGen slot 1 were concurrently running; this was not an intentional five-replica configuration.

Evidence proves the unsafe policy, task churn, overlapping task generations, failed health execution and host-wide OOM. **It does not prove the complete scheduler sequence that produced all five simultaneous generations, or which exact application startup operation each reached.** The old tasks/containers and their application/probe histories have been removed by recovery/reconciliation. `docker service ps` now returns no rows, and `docker ps -a` filtered by service returns no containers. We cannot reconstruct missing per-task state transitions honestly from a service specification alone. No exact Docker/Swarm defect or single CPU-hot function is claimed.

### Timeline (UTC)

| Time | Evidence |
| --- | --- |
| Before recovery build | Swarm repeatedly failed to find the local backend image; public API 502. Journald confirms attempts approximately every five seconds. |
| 02:49:46–02:53:44 | First recovery build completed, producing `a0ba38786ae8…`. Container logs previously captured the Python 3.11 SyntaxError in `voice/service.py`. Tasks repeatedly exited 1. |
| 03:02:28–03:04:18 | Unpatched Rebuild was cancelled. Build log ends with context cancelled. |
| 03:04:44–03:12:18 | Patched Deploy completed image `sha256:11d46dd53dc42b1cfb4e9022ed389e9004ac519fd914cf0dc7532351507c52c3`. Dokploy database reports done; image/build log confirms completion. Image metadata Created is 03:10:50, before layer export completed. |
| Through 03:12:32 | Daemon logs still show NexGen task exit-1 failures and fresh task IDs. Per-task image IDs were not retained, so failures after the service update must not all be assigned to the patched image. |
| 03:13:31 | Manager heartbeat deadline exceeded (journal arrival 03:13:39). |
| 03:23:12 | First retained global OOM kill in the queried incident window. Docker also times out starting health probes for multiple containers. |
| 03:50, 03:53, 04:05, 04:11, 04:21 | Further global OOM kills. At 04:21, victim container ID `86bd16a18ffd…` matches Dokploy in the user's stats. Thus the control plane was directly affected. |
| 04:11:48 | The five supplied NexGen task IDs appear together in image-pull warnings. Local image fallback exists; a pull warning alone does not mean these tasks never ran. |
| 04:14–04:21 | All five supplied container IDs have daemon warnings: health-check process could not be started within the engine deadline. |
| 04:21:21–22 | All five have `Container failed to exit within 10s of signal 15`; Docker escalates termination. This proves shutdown difficulties, not that the earlier “Could not send KILL” messages necessarily referred to the main app rather than an exec probe. |
| 04:59:09 | Current service update timestamp after user recovery/scaling to zero. |

The three latest builds were sequential according to recorded start/finish times. **There is no evidence that simultaneous image builds caused the five containers.** One expensive on-host build overlapped an already failing runtime service; task replacement continued afterward.

### Why health remained starting

The retained image checks HTTP `127.0.0.1:8000/health` via Python urllib; its configuration is 30s interval, 10s engine timeout, 5s request timeout, 60s start period, three retries. No live service health override is present. Python exists in the image; curl/wget is not required. Uvicorn binds `0.0.0.0:8000`, matching the probe.

The logs for **each of the five containers** say `timed out starting health check`, which is distinct from an HTTP error returned by `/health`. Docker was struggling to launch the probe itself. Moby 28.5.0 implements a separate 30-second exec-start deadline before the configured request/probe execution timeout. Under severe daemon scheduling/locking pressure, wall-clock health-state convergence cannot be inferred from the Dockerfile timings alone. The missing per-container health histories prevent proving every transition that left their displayed state at starting. Increasing the start period would not repair an overloaded control plane.

Application startup additionally blocks serving until DB pool creation, local model loading and embedding warmup finish. `/health` executes a DB `SELECT 1`; it is readiness, not independent liveness. No evidence currently proves a wrong path, port, missing curl, Supabase outage, migrations, or Retell API call caused this health failure.

## B. Contributing factors, verified configuration

| Setting | Actual audit observation | Consequence |
| --- | --- | --- |
| Intended replicas | Dokploy 1; previous Swarm spec 1; current Swarm 0 | No configured five-replica deployment. |
| Duplicate applications | One matching Dokploy backend application row | No second matching application found; five names share slot 1. |
| Update | start-first, parallelism 1, rollback on failure, monitor 5s, failure ratio 0 | Temporary overlap allowed; monitor does not cover the startup/health window. Does not alone explain five generations. |
| Rollback | start-first, parallelism 1, pause on failure, monitor 5s | Rollback can also overlap heavyweight processes. |
| Restart | any, 5s delay, MaxAttempts 0/unlimited | Permanent startup failure repeatedly consumes runtime/manager work. |
| Resource limits/reservations | Empty live; null in Dokploy | No NexGen CPU/RAM boundary; host OOM can kill Dokploy. |
| Stop grace | 10s live default | Logs confirm tasks exceeded it; extending it alone cannot fix saturation. |
| Image identity | Local mutable `…tok2fu:latest`, no immutable registry reference | Rollback/retry cannot reliably identify a previously good artifact after retagging. |
| Build location | buildType dockerfile, sourceType github, serverId/buildServerId null | Build runs on the production manager. |
| Build cost | pip step 266s; model-cache step 53s; export 87s; image 1.73 GB | Significant manager-host resource exposure; runtime limits do not limit the build. |
| Deployment concurrency | buildsConcurrency=1; v0.30.0 per-application FIFO | Same-app builds are serialized; repeated requests are queued, not deduplicated. |
| Completion | Dokploy submits service update and immediately marks deployment done | Queue serialization does not wait for healthy Swarm convergence. |
| Workers | One Uvicorn process by command/default; no WEB_CONCURRENCY in service env | Multiple containers, not a configured Gunicorn/Uvicorn worker farm. Other npm/Postgres processes belong to the shared host; no npm in backend Dockerfile. |
| Logs | json-file daemon default; no service LogDriver override | No per-service rotation guarantee was verified. |

Dokploy v0.30.0 source was inspected at tag commit `e541308a4f96ca7358ba81ffd53b01b9479c5e19`. It supplies these start-first defaults when JSON overrides are null. Its Dockerfile build command does not apply the application's runtime CPU/memory limits. Its application mechanization uses the existing named service and increments ForceUpdate; it does not wait for convergence. The installed image is tagged v0.30.0; the upstream tag review is not a byte-for-byte attestation of the installed bundle.

## C. Files/configurations responsible and prior-build comparison

- `/etc/dokploy/applications/nexgenclothing-lifestyle-nexgenbackend-tok2fu/code/Dockerfile` and the repository `Dockerfile`: heavyweight on-host dependency/model build; health check coupled to DB; thread counts not bounded originally.
- Repository `backend/app/main.py:30`: synchronous pool/model/warmup before startup completes; originally lacked a log identifying the stage before model loading.
- Repository `backend/app/rag/embeddings.py:89`: one model per process, cached per process; no application process spawning here.
- Repository `backend/app/api/routes_meta.py:12` (pre-patch): database-aware `/health`.
- Repository `backend/app/db.py`: two minimum/ten maximum DB pool connections; no migrations or seed invocation.
- Dokploy application `kNKuOmx16MVTd4Y71Wk1D`; Swarm service `pfeo8l8lgz6kn9px12nros4cq`: defaults and absent resource/restart controls above. There is no repository Compose/Swarm deployment definition controlling this application; adding a Compose file alone would not change the existing Dokploy Application.

Commit `f2ba6d7` previously pushed changes only the Python 3.11 regex/f-string compatibility issue and the compileall build gate. The server checkout remains `0653a4d` plus those two saved patches. No changes were made to credentials, startup migrations, ports or production data. The compile gate executes at build time and does not load the model.

The September 10 retained build produced `ebcbe057af48…`, but that artifact is not established as a healthy rollback target. Its log shows threadpoolctl 3.6.0 and tqdm 4.70.0; September 16 used 3.7.0 and 4.70.1. Other displayed primary package versions match. Floating base/transitive dependencies mean identical Git source does not imply an identical artifact. No evidence links these two dependency differences to the incident; do not downgrade them speculatively.

## D/E. Required fixes and minimal local patch

### Prepared locally, not deployed

1. `backend/app/api/routes_meta.py`: add dependency-free async `/livez`. Preserve `/health` and its database-aware response contract as readiness. A DB interruption after startup no longer needs to trigger Docker liveness replacement. Liveness still only becomes reachable after normal ASGI startup; no feature is falsely declared ready while the model initializes.
2. `Dockerfile`: probe `/livez` using exec-form Python; explicitly `--workers 1`; set OMP/MKL/OpenBLAS threads to 1 and tokenizer parallelism false. Keep model/provider, warmup, port, runtime, dependencies and 60s grace unchanged. Thread constraints may increase single-request latency and need representative voice/search testing.
3. `backend/app/main.py`: log pool/model/warmup stages, failure stage/type and completion; close the pool on failed startup as well as shutdown. No model/lifecycle redesign or DB changes. Our new failure message omits exception text; existing framework tracebacks must still be treated as private logs.
4. `deploy/nexgen-backend-safety.json`: reviewable Dokploy field values with replicas/mode **0** and autoDeploy false, stop-first update/rollback, pause on update failure, finite rapid-failure restart policy and resource budget. This is an operator input artifact, not an automatically loaded configuration. Top-level metadata/logging/qualification fields are not API application fields. Only `dokployApplicationUpdate` corresponds to that update payload.
5. `tests/test_production_health.py`: offline regression tests for independent liveness, retained DB readiness, startup failure diagnostics/cleanup and retained warmup.

### Required operational changes, still NOT applied

- Persist hold state and disable auto-deploy for **this application only**. Both `replicas` and `modeSwarm.Replicated.Replicas` must remain zero until separately approved; explicit mode takes precedence in Dokploy. Later restore both to one. Do not submit a deployment just to save the hold settings.
- Move image builds to a non-production builder; deploy a tested immutable registry digest. Do not add a production push-triggered build workflow in this audit. Keep the current on-host build path unused until provider/build migration is deliberately approved.
- Use stop-first/parallelism one for update and rollback, failure action pause, 180s monitor, zero failure ratio. Pause is chosen because **no known-good immutable rollback image has been validated**. Once one exists, an explicit controlled rollback can use it without rolling back resource protections.
- Candidate steady policy: on-failure, delay 60s, max attempts 2, window 600s. This bounds rapid failures; it is not a lifetime restart cap. Later long-lived failures and manual deployments can reset retry accounting. Qualification container uses restart=no; rollout failure must be contained back to zero.
- Candidate resource envelope: 0.75 CPU and 1 GiB hard limits, with equal reservations to reserve the whole admitted budget. The recovered host had ~2 GiB available and >94% interval idle. The memory cap leaves roughly 1 GiB of that headroom; the CPU cap consumes at most 37.5% of the two-CPU host for a single container. **These are conservative admission budgets, not measurements of a successfully running model.** Fail qualification if it cannot start within 60s or peaks above 768 MiB (25% margin under cap), rather than automatically raising limits. Other workloads' peaks remain unknown; remeasure immediately before admission.
- json-file rotation 10m × 3 per task. Dokploy's reviewed Application builder does not set TaskTemplate.LogDriver, so a manual service override can be lost on its next deployment. The approved release procedure must apply and verify it before starting tasks; do not modify global daemon logging or unrelated projects.
- Avoid repeated manual Deploy clicks. Built-in per-app FIFO prevents simultaneous builds, but does not deduplicate queued releases or wait for runtime health. Use one application-specific release lock covering update, readiness/resource observation and failure containment. All NexGen release paths must use that gate; a shell lock cannot constrain independent UI/webhook actions. Auto-deploy stays disabled. No global queue/settings changes are needed.

Per-container limits and stop-first reduce blast radius; **no honest guarantee of “never affects the host” is possible on a shared kernel with unbounded unrelated services or a wedged Docker daemon**. Prevent builds on the manager, constrain the sole admitted task, verify no orphan tasks before starting, and stop on nonconvergence. Do not claim per-container CPU limits create an aggregate limit across arbitrary orphaned containers.

## F. Validation completed and withheld

| Check | Result |
| --- | --- |
| Offline backend regression suite | 362 passed; zero failures/errors/skips; Python 3.14.7; live DB connections/pool blocked. Includes preserved pre-existing user edits. |
| Production-runtime syntax | All 97 backend Python files compile under actual Python 3.11.9. |
| Health semantics | TestClient `/livez` 200 even with unavailable DB; existing `/health` fails with unavailable DB and returns original 200 payload with mocked SELECT 1. |
| Lifecycle | Model failure does not yield startup readiness; stage logged; pool closed; successful warmup retained. |
| Policy artifact | JSON parses; zero/zero hold consistency, stop-first, finite retry values, resource relationships checked. |
| Diff whitespace | git diff --check passes (line-ending warnings only). |
| Production image configuration | Retained image inspected without starting it; command/port/probe verified. |
| New container image startup, actual probe, model CPU/RAM | **Not run. No rebuild or production container start authorized.** Local Docker works, but no NexGen image is present locally. |
| Live app login/catalogue/voice | Not run; backend intentionally off. Earlier frontend tests remain historical results, not new end-to-end certification. |

Full outputs: `reports/nexgen_deployment_safety_tests.txt` and `.json`. Fifteen live Tool Gateway tests were excluded to avoid audit/commerce writes; this is not an all-tests-in-production claim.

## G. Safe future build and qualification procedure

**Run only after the audit is accepted and a non-production build/test is explicitly approved.** No command below has been executed during this audit. Production remains zero throughout qualification.

1. Review only this incident's diff; preserve unrelated user changes. Remove/reconcile the two old full-file Dokploy patches before a future source deploy because they can overwrite this new Dockerfile or newer voice code. Do not push while auto-deploy remains enabled.
2. On a non-production Linux builder/Codespace with Docker, build the intended clean revision once; do not use the VPS Docker context. Use a unique revision tag, preserve logs and resolve/preserve the resulting image digest. Serialize this application’s CI workflow (one concurrency group, no production deploy hook); do not cancel a release during its verification phase.
3. Example local-builder command after approval: `docker build --tag nexgen-backend:qualification -f Dockerfile .`. A dedicated BuildKit worker may use max-parallelism=1; this is a concurrency control, not a RAM guarantee. Do not rely on runtime limits to limit the image build.
4. Supply a staging or dedicated read-only test DB connection in a private env file outside the build context. Do not copy production admin/SMTP/Retell secrets into the test. Required startup uses DB and the cached local model; no external voice request is needed for health qualification. If using a staging snapshot, keep migrations/seeding separate and explicit.
5. Confirm no previous `nexgen-backend-qualification` container exists; if one exists, inspect it rather than overwriting/removing it. Start exactly one container on the **non-production Docker context**:

```sh
docker run -d --name nexgen-backend-qualification \
  --restart=no --cpus=0.75 --memory=1g --memory-swap=1g --pids-limit=128 \
  --log-driver=json-file --log-opt max-size=10m --log-opt max-file=3 \
  --env-file /secure/path/nexgen-qualification.env \
  -p 127.0.0.1:18000:8000 nexgen-backend:qualification
```

6. Within 60s verify startup-complete logs, both endpoints and effective process/health settings:

```sh
docker logs --timestamps --tail 100 nexgen-backend-qualification
curl --fail --max-time 5 http://127.0.0.1:18000/livez
curl --fail --max-time 5 http://127.0.0.1:18000/health
docker inspect nexgen-backend-qualification --format '{{json .State.Health}}'
docker top nexgen-backend-qualification -eo pid,ppid,comm,nlwp
docker stats --no-stream nexgen-backend-qualification
```

7. Observe for at least 10 minutes, sampling CPU/RAM during startup, idle and representative read-only search/voice-tool workload against test data. Inspect cgroup v2 memory.peak/memory.events and cpu.stat where supported; do not infer peak memory from one docker stats sample. Verify one Uvicorn process; temporary health-probe processes and library threads are not extra application workers. Fail on restart, OOM, health regression, persistent CPU saturation, startup >60s or peak >768 MiB. Save logs before stopping.
8. Stop only this named test container: `docker stop --time 30 nexgen-backend-qualification`. Preserve it/logs for review; no volumes or images need deletion. A separate deliberately invalid DB test may be run sequentially in the non-production environment to confirm failed readiness and bounded failure; do not overlap tests.
9. Publish the qualified artifact to an approved registry and record a `registry/repository@sha256:...` reference. The registry must be chosen/configured before this step; no invented destination or credentials are included here. Verify startup of that exact digest rather than rebuilding after qualification.

### Eventual production configuration and release (separate approval)

Save the proposed hold-state settings in Dokploy without deploying. Switch this app to the approved immutable Docker image source and remove the old overrides as appropriate. A single release owner must hold an app-specific lock through qualification of the runtime. For an SSH-managed release gate, `flock` can protect `/run/lock/nexgen-backend-release.lock`; keep manual UI/webhook deployments disabled because they do not honor this lock.

Before starting anything, assert current mode replicas zero, zero actual backend containers, no queued/active NexGen deployment, responsive Docker API, adequate free headroom and healthy baselines for other apps. Fail closed on any mismatch. Apply required Swarm overrides while replicas remain zero, then inspect that all fields persisted; this is an example future command, not an applied change:

```sh
docker service update --detach=true --replicas 0 \
  --limit-cpu 0.75 --reserve-cpu 0.75 \
  --limit-memory 1G --reserve-memory 1G \
  --update-order stop-first --update-parallelism 1 --update-delay 30s \
  --update-monitor 180s --update-failure-action pause --update-max-failure-ratio 0 \
  --rollback-order stop-first --rollback-parallelism 1 --rollback-delay 30s \
  --rollback-monitor 180s --rollback-failure-action pause --rollback-max-failure-ratio 0 \
  --restart-condition on-failure --restart-delay 60s \
  --restart-max-attempts 2 --restart-window 600s --stop-grace-period 30s \
  --log-driver json-file --log-opt max-size=10m --log-opt max-file=3 \
  nexgenclothing-lifestyle-nexgenbackend-tok2fu
```

Select the qualified immutable image while still at zero (`docker service update --detach=true --replicas 0 --image "$APPROVED_IMAGE_DIGEST" ...`, with a verified full digest value). Do not use the current mutable latest as a substitute. Confirm the service's effective health check comes from the new image and that Dokploy saved fields match the gate. Only after separate restoration approval change the saved normal count/mode to one and issue `docker service scale --detach=true nexgenclothing-lifestyle-nexgenbackend-tok2fu=1`. Observe one stable task and both liveness/readiness, retain the lock for the 10-minute observation, and contain back to zero immediately on failure. Do not release the gate merely because the update API returned success.

## H. Rollback / containment

The known safe fallback today is OFF, not the old broken image:

```sh
docker service scale --detach=true nexgenclothing-lifestyle-nexgenbackend-tok2fu=0
docker service inspect nexgenclothing-lifestyle-nexgenbackend-tok2fu --format '{{json .Spec.Mode}}'
docker ps --filter label=com.docker.swarm.service.name=nexgenclothing-lifestyle-nexgenbackend-tok2fu
```

Also preserve the application hold at replicas/mode zero with auto-deploy disabled so another trigger cannot undo it. A timed-out command may have been accepted; inspect state before repeating a mutation. If the manager becomes unresponsive, do not repeatedly force-update or restart other services. Escalate recovery access without automatic Docker-wide restarts/pruning.

For a future known-good artifact rollback: first contain to zero and verify no backend tasks remain; set the recorded approved previous digest while retaining the **new** resource/restart/logging controls, qualify its readiness, then restore one only with approval. Do not blindly use `docker service rollback`: PreviousSpec currently relates to the mutable latest/old unsafe policy and may restore settings that caused this incident. No verified previous healthy digest exists yet.

## I. Pre-rebuild gates and post-deployment checklist

| Requested gate | Status |
| --- | --- |
| Root cause identified | Unsafe containment/OOM/control-plane failure confirmed; exact five-generation scheduler history and last application startup stage not fully recoverable. |
| Health locally/container-side validated | Local route semantics pass; new-image container test pending approval. |
| Intended replicas one | Confirmed; hold zero preserved. |
| Update strategy reviewed | Confirmed unsafe defaults; stop-first candidate prepared, not applied. |
| Restart bounded | Candidate prepared, not applied. |
| Resource limits | Budget reviewed/prepared; requires isolated measured qualification. |
| Worker count | Actual image default one; patch makes explicit. |
| Concurrent deployments | Built-in FIFO verified; full rollout lock/trigger restrictions still operational work. |
| Rollback configured | Safe zero fallback documented; policy artifact prepared, not applied. |
| No destructive startup DB work | Verified source pool/model startup; no migration/seed call. |
| Build reviewed | On-manager heavy build confirmed; off-host artifact flow required. |
| New image starts in isolation | Pending; no rebuild performed. |
| Health returns 200 | Local mocked readiness + independent liveness pass; real container readiness pending. |
| Unrelated projects untouched | Yes. |

After eventual approval/restoration, verify and record:

- [ ] NexGen backend desired/actual `1/1`, exactly one active backend container and one Uvicorn worker.
- [ ] Stable task/container ID for 10 minutes; no repeated failure/replacement events.
- [ ] Docker health healthy; `/livez` and database-aware `/health` return 200.
- [ ] CPU idle remains meaningful; memory stays within the qualified envelope with host headroom.
- [ ] `timeout 5s docker info` succeeds; Dokploy UI and Traefik respond; a fresh SSH connection succeeds.
- [ ] NexGen frontend and BDS/NexDrive/LensCraft/other previously active services retain their baseline replica counts and HTTP health.
- [ ] Catalogue/search/product detail, customer login/reload/logout and Retell audio/tool turn pass manual acceptance.
- [ ] Service inspect confirms stop-first, finite rapid-failure retries, resource limits, one replica, immutable digest and bounded logging after Dokploy actions.
- [ ] No pending duplicate NexGen deployment; release lock held until all checks pass; rollback digest/logs recorded.

Suggested read-only checks: `uptime`, `free -h`, `vmstat 1 5`, `docker stats --no-stream`, `docker service ls`, targeted `docker service ps`, `docker ps`, and bounded `docker logs`. Avoid full inspect dumps that expose environment secrets.

## Subsequent isolated qualification

The user subsequently authorized local off-production testing. The image build, 10-minute constrained container run, 11 catalogue/health checks, database-outage probe separation and failed-startup test passed. Startup was 17.626 seconds and peak cgroup memory was 389.39 MiB under 0.75 CPU/1 GiB. Full results and limitations are in [the qualification report](nexgen_container_qualification_2026_09_16.md). Earlier pending-test entries above describe the audit-time state; isolated runtime gates are now satisfied for the synthetic workload only. Deployment policy remains unapplied, production remains 0/0, and production rebuild is not cleared.

## Primary references

- Docker 28.5.0 probe execution implementation: https://github.com/moby/moby/blob/v28.5.0/daemon/health.go
- Docker service update settings: https://docs.docker.com/reference/cli/docker/service/update/
- Docker service scale: https://docs.docker.com/reference/cli/docker/service/scale/
- Dokploy 0.30.0 defaults: https://github.com/Dokploy/dokploy/blob/v0.30.0/packages/server/src/utils/docker/utils.ts
- Dokploy 0.30.0 service update: https://github.com/Dokploy/dokploy/blob/v0.30.0/packages/server/src/utils/builders/index.ts
- Dokploy 0.30.0 queue: https://github.com/Dokploy/dokploy/blob/v0.30.0/apps/dokploy/server/queues/in-memory-queue.ts
