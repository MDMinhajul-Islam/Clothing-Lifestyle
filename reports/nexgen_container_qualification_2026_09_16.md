# NexGen isolated container qualification — 16 September 2026

## Scope and decision

The user authorized off-production tests. No VPS build, deployment, scale-up, configuration change, commit or push was performed during this qualification. Production backend remains deliberately stopped. Local qualification is not authorization or proof of safe production rollout.

**Isolated qualification passed. Production rebuild is NOT cleared.** Final measured results are recorded in `nexgen_container_qualification.json` and `nexgen_failed_startup.json`.

## Final results

| Check | Observed result |
| --- | --- |
| Constrained local image build | Passed; Python 3.11 compile gate and model cache completed |
| Startup under 0.75 CPU / 1 GiB | 17.626 seconds; below 60-second gate |
| Catalogue and health HTTP checks | 11 recorded checks passed, including 5 search queries |
| Stability | 600 seconds before fault injection; 25 healthy samples including post-outage observation |
| Memory peak | 389.39 MiB; below 768-MiB qualification ceiling and 1-GiB hard limit |
| Steady observation CPU | About 1.94% of one core between seconds 257 and 600, including probes; not a loaded-traffic benchmark |
| OOM / container restart | Zero / zero; restart policy deliberately disabled |
| Process snapshot | One application Python/Uvicorn process, 8 threads; explicit workers=1 |
| Database outage after startup | `/livez` 200, `/health` 500, Docker health still healthy after 35 seconds |
| Unreachable DB during startup | Expected exit code 3 in 2.796 seconds; database_pool failure stage logged; zero restarts/OOM |
| Shutdown / cleanup | Backend and local DB stopped; build helper stopped; no matching test containers running |
| Total successful main run | 642.275 seconds including fault injection and shutdown |

The failure-startup test used network=none and a dummy localhost connection, with the same image and runtime caps. Expected failure is a passed negative test. The Docker restart policy was disabled intentionally: these tests do not exercise or prove the proposed Swarm retry/update policy.

## Artifact and isolation

- Source: clean archive of committed HEAD `f2ba6d70be90807b462afd6993b5f27b186543f0`, with only the proposed Dockerfile, `backend/app/main.py`, and `backend/app/api/routes_meta.py` overlaid. Existing unrelated working-tree voice changes were excluded.
- Image: local `nexgen-backend:qualification-20260916`, Docker image identity `sha256:07b7148c579d926e47caa8f89fafb05de38f6b8efeee4911880def10a852ff45`. Not published to a registry.
- Build: local Docker Desktop dedicated BuildKit builder, one CPU, 2 GiB memory/no extra swap, maximum build parallelism one. Python 3.11 syntax compilation and cached embedding-model build completed successfully. Builder stopped afterward.
- Backend: one container, one Uvicorn process, 0.75 CPU, 1 GiB memory/no extra swap, 128 PID limit, no automatic restarts, bounded JSON logs. Effective Docker limits were inspected.
- Database: separate local pgvector PostgreSQL 17, 0.5 CPU/512 MiB, internal Docker network, synthetic data only: 6,000 products, 36,000 variants and 6,000 vectors. Applied catalogue/vector migrations 001, 002 and 009 locally. Backend role has SELECT-only permissions and verified read-only transactions.
- HTTP checks run inside the container against loopback, matching the Docker health-probe path. Reported durations include Docker exec overhead; they are not server-only latency benchmarks.

## Coverage and limits

The runtime exercise checks startup, liveness, database readiness, catalogue list/facets/styled edit/product details and multiple semantic searches, followed by ten minutes of bounded observation and a local database outage. A separate sequential test checks failure with an unreachable database and no network access.

Earlier regression evidence: 362 offline backend tests passed (zero failures/errors); 15 live Tool Gateway integration tests were deliberately excluded to avoid business-data writes. The suite ran on host Python 3.14.7. Production Python 3.11 compilation and this real Python 3.11 container exercise complement it; they do not mean all 362 tests were rerun inside the image. Frontend's previously recorded 12 tests/build were not rerun in this qualification; frontend source is unchanged.

This is not a concurrent-user load test. Synthetic vectors do not validate live recommendation relevance. Existing customer-password verification, browser cookies/CORS, Retell audio/webhooks, SMTP and live commerce write flows still require controlled acceptance testing. Docker Desktop differs from the Ubuntu/Docker 28.5 production host. No local test establishes that the VPS can safely absorb a build or reproduce historical Swarm scheduler behavior.

## Aborted attempts, retained for transparency

1. An initial local container started against the existing Supabase connection in 21.167 seconds, but the read-only transaction guard was not active despite connection startup options. The runner aborted before catalogue/business calls. This was a test isolation failure, not an application-startup failure. No production writes were executed. That stopped, newly created, mount-free local container was selectively removed to clear its credential-bearing metadata; the environment file was replaced with local credentials. Evidence: `nexgen_supabase_qualification_aborted.json` and log.
2. A local-database attempt completed application startup in about 11 seconds and its Docker probe returned 200, but the host-side runner could not reach the published endpoint through the isolated network. It stopped at the startup deadline. The runner was corrected to use container-side checks without changing/rebuilding the image. Evidence: `nexgen_host_probe_aborted.json` and log.

## Production read-only snapshot

At server time 05:42:03 UTC: load 0.10 / 0.16 / 5.06; available memory 1,918 MiB; no swap. Backend 0/0, frontend 1/1. Previously active Swarm services remained 1/1; previously stopped services remained 0/0. This does not assert HTTP acceptance of every unrelated application.

Available memory was below the proposed 2,048-MiB pre-deployment gate. The saved Dokploy safety policy is still only a proposal. Auto-deploy/replica drift, persistent Dockerfile overrides, immutable artifact publication, stop-first updates, restart bounds and effective resource/log limits must be resolved and verified before any restoration. Do not click Rebuild on the shared VPS based solely on these tests. The detailed audit contains the deployment gates and containment-to-zero procedure.
