# NexGen controlled production restoration — 16 September 2026

**RESTORED:** Backend is 1/1 and healthy on the qualified immutable GHCR image. Ten minutes of observation after readiness passed. Public `/health` returned `status=healthy`, `environment=production`, `database=connected` in the final check. No rebuild, new image, application-code edit, Git commit/push or frontend deployment occurred in this restoration.

## Memory decision

The earlier 2,048-MiB available-memory requirement was an agent-chosen conservative admission gate, **not a Docker Swarm, Dokploy or backend-image requirement**. Treating it as mandatory unnecessarily blocked recovery. This restoration supersedes that gate; no application code or image was changed.

Docker distinguishes a container hard memory limit from a service reservation used for placement. A 1-GiB limit does not require 2 GiB currently available. Reservations are scheduling constraints, not a guarantee that unrelated unbounded containers cannot grow. See [Docker resource limits](https://docs.docker.com/engine/containers/resource_constraints/) and [Swarm resource reservations](https://docs.docker.com/engine/swarm/services/#reserve-memory-or-cpus-for-a-service). Dokploy 0.30.0's inspected builder passes the configured limits/reservations to Swarm; no 2-GiB MemAvailable admission rule was identified. The image has no host-memory preflight rule.

Evidence before this restoration:

- Same qualified image started locally in 17.626 seconds with 389.39-MiB cgroup peak, 0.75 CPU and 1-GiB hard limit. Synthetic database workload and Docker Desktop differ from production.
- VPS inspection showed 1,908 MiB available, zero recent memory PSI averages and no kernel OOM entries during the preceding 15 minutes. The actual release preflight recorded 1,887 MiB available.
- At preflight, the full 1,024-MiB backend cap left approximately 863 MiB of measured availability beyond that cap. CPU was largely idle. This supported a controlled single-task attempt with active failure monitoring; it is not a guarantee for arbitrary future traffic.
- No reliable successful historical deployment memory baseline survived the incident. Five failing overlapping tasks and the previous global OOM are not evidence of healthy historical capacity.

The release guard checked current availability against the full task cap and active memory stalls, rather than requiring twice the cap. During execution it monitored host OOM counter, container cgroup OOM, health, task identity, memory availability and severe memory stalls. A failure triggers targeted scale-to-zero and saved Dokploy hold; it does not restart Docker or touch other services.

## Artifact and execution

Pulled the existing private image by digest:

`ghcr.io/mdminhajul-islam/nexgen-backend@sha256:07b7148c579d926e47caa8f89fafb05de38f6b8efeee4911880def10a852ff45`

The platform image config identity on the VPS is `sha256:c76e25f9daf2ac2eb86ac45e62d7e1c889a88706ecd107df752468f077ce3e7b`; this is the config within the qualified manifest, not a different rebuild. Verified inherited `/livez` health check and one-worker command before starting.

Only the existing NexGen backend service was updated. The release held an application-specific lock, verified no running deployment records or existing backend containers, saved prior state root-only, authenticated with the saved private-registry credential, pulled without building, selected the digest at replicas zero, then scaled to one. Registry auth was passed to Swarm; the temporary CLI auth file was removed afterward. Existing environment, routes, network and database were retained. Frontend service was not updated.

Safety controls remain: 0.75 CPU and 1-GiB memory cap/reservation, stop-first update/rollback, parallelism one, pause on failure, 60-second restart delay/max two failures within 600 seconds, 30-second stop grace and JSON logs 10 MiB × 3. Autodeploy remains disabled. These bounded retries are not a lifetime prohibition on restarts.

Startup logs were continuously followed into root-only `startup-live.log`; Docker events were simultaneously captured. Database pool stage began 06:23:33 UTC, embedding model initialized in 22.882 seconds, warmup took 273 ms, application startup completed at 06:23:59 UTC. Public readiness was observed at 34.36 seconds after scale-up.

## Smoke-test evidence

Initial seven API checks passed: `/livez`, database-aware `/health`, product list, facets, semantic search, tool definitions and expected unauthenticated `/me` rejection.

Fourteen additional HTTP checks returned their expected statuses:

| Check | Result |
| --- | --- |
| Product listing/detail/styled edit/search | 200; default listing reports 5,905 products |
| Browser-origin CORS | Exact production frontend origin returned on all 14 responses |
| Unauthenticated profile | 401 as expected |
| Login with unique nonexistent test email | 401; no existing account failure counters touched |
| AI orchestrator without secret / with secret | 401 / 200; valid request routed to TOOL_GATEWAY |
| Retell unsigned / signed lifecycle webhook | 401 / 200 |
| Authenticated mock voice session | 200; session created for smoke test |
| Signed `nexgen_voice_turn` greeting | 200 with nonempty spoken_text |
| End smoke voice session | 200; in-memory test session closed |
| Retell create-web-call | 201 and access token received; token not printed |

Read-only aggregate queries confirmed existing credential/session tables are accessible (3 credential rows, 7 session rows at test time). An ephemeral Argon2 hash/verify self-test passed without changing a customer password. This is not a successful existing-password login test; the user agreed to verify their own account in the browser.

Live browser inspection showed actual product images, prices, availability and **24 products shown / 5,905 matching**. The browser also displayed a restored signed-in customer session. No frontend redeployment was needed. The total is the API's current public listing count, not a claim that every raw database product must appear unfiltered.

No real order, exchange, refund, SMTP email, password reset or customer record mutation was performed. One Retell web room was created to verify authorization; no audio connection was started by the agent. Audible greeting, microphone/playback and a complete live spoken conversation remain a separate acceptance boundary. Signed synthetic webhook/function tests prove application handling, not an actual Retell-origin event delivery.

## Observation

The full 10-minute observation after readiness **passed**. Total pull/start/observation execution took 684.4 seconds. Same container `66eb5fd87cc5` remained running; restart count zero, host OOM delta zero, cgroup max/OOM/oom_kill counters zero throughout. Peak reached 807.61 MiB, including the extra Argon2 smoke-test process. This exceeds the earlier local-test-only 768-MiB qualification target, but remains below the unchanged 1-GiB hard cap and is not an OOM or unsafe-startup event. Minimum sampled host availability after readiness was 1,466 MiB; final availability was 1,480 MiB.

Saved Dokploy replicas and explicit Swarm mode were set to one only after successful observation, and live/saved safety settings were rechecked. Autodeploy remains false. All other service replica counts, including frontend 1/1, match the baseline. Application logs contained zero ERROR/Traceback lines during the checked interval. Dokploy emitted no log lines during that interval; it remained running. Kernel and container events were retained root-only with the release evidence.

Container events recorded one create, one start and one transition to healthy, with no container die/OOM event. The `exec_die` entries are completed health probes/test subprocesses, not backend exits. Kernel post-release query returned no OOM entries. Final load averages were 0.51 / 0.41 / 0.49.

Machine-readable evidence: `nexgen_production_restoration_metrics.json` and `nexgen_restored_service_settings.txt`. Full root-only operational evidence remains in `/root/nexgen-recovery/controlled-20260916/`; snapshots there contain environment/registry data and must not be published. The application-specific release lock was released after completion; continuous agent supervision is no longer running. Docker health checks, hard limits and bounded restart policy remain active.

Fresh successful password login awaits the user's report; the browser's restored signed-in state was observed. Audible Retell conversation remains unverified. These acceptance limits do not negate successful backend/database/catalogue recovery. No production blocker was observed in the completed checks. Future workload growth still requires monitoring; the observation is not a concurrent-load capacity certification.

At one measured steady sample, cgroup usage was 720.39 MiB: 355.34 MiB anonymous and 346.33 MiB file cache, with 135.95 MiB inactive file cache. Docker stats subtracts inactive cache and reported about 584 MiB. This explains why Docker stats and cgroup totals differ; it does not establish every cause of the difference from local testing.
