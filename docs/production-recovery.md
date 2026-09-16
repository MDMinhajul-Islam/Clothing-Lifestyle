# Production recovery and deployment controls

## Qualified release (16 September 2026)

The backend was restored using the existing private image, without rebuilding on the shared VPS:

```text
ghcr.io/mdminhajul-islam/nexgen-backend@sha256:07b7148c579d926e47caa8f89fafb05de38f6b8efeee4911880def10a852ff45
```

The image was built from commit `f2ba6d70be90807b462afd6993b5f27b186543f0` plus the Dockerfile, metadata routes and startup lifecycle changes recorded alongside this document. Unrelated in-progress voice changes were excluded. This commit records the deployed source changes; pushing it does not require a redeployment.

Dokploy uses the Docker provider and the immutable image reference. Autodeploy is disabled. Normal backend replica count is one, in both the application replica field and explicit Swarm mode. Frontend deployment is unchanged.

## Runtime controls

| Setting | Value |
| --- | --- |
| CPU limit / reservation | 0.75 / 0.75 CPU |
| Memory limit / reservation | 1 GiB / 1 GiB |
| Uvicorn workers | 1 |
| Numeric-library thread settings | OMP, MKL and OPENBLAS: 1; tokenizer parallelism disabled |
| Update / rollback | stop-first, parallelism 1, delay 30s, monitor 180s, pause on failure |
| Restart | on-failure, delay 60s, max attempts 2 within 600s |
| Stop grace period | 30s |
| Live service logging | json-file, max-size 10m, max-file 3 |

Verify the effective settings after any future Dokploy action; do not assume every setting, particularly log rotation, survives a provider-generated service update. Bounded restarts apply within the evaluation window, not across the entire service lifetime.

`/livez` checks application liveness after startup and does not query the database. Docker uses this endpoint. `/health` retains the database-aware readiness contract, including `SELECT 1`. A database outage should fail readiness without causing otherwise-live application processes to churn. External readiness monitoring must check `/health` as well as Docker health.

Startup logs identify database-pool, embedding-model and embedding-warmup stages. Cleanup closes the pool even if startup fails. Model initialization and warmup remain enabled.

## Measured validation

- Four focused offline health/lifecycle tests pass. Earlier safe backend regression run: 362 passing tests; 15 live Tool Gateway tests excluded to avoid production business writes.
- Isolated image qualification: startup 17.626s; peak cgroup memory 389.39 MiB; ten-minute stability, database-outage and invalid-startup checks passed.
- Production restoration: startup 34.36s; ten minutes after readiness passed with one stable container, zero restarts and zero host/container OOM events.
- Production peak was 807.61 MiB during smoke testing, including an additional Argon2 test process. Minimum sampled host availability after readiness was 1,466 MiB.
- Health/database, catalogue/detail/search, CORS, protected authentication/AI endpoints, signed Retell webhook/function and Retell web-call token creation passed their smoke checks. Browser displayed 24 products and 5,905 matches; product detail and search also worked.
- Existing browser session restoration was observed. Fresh password login and audible end-to-end Retell conversation remain manual acceptance items. These checks are not a concurrent-load capacity certification.

The former 2,048-MiB available-RAM gate was a conservative investigation assumption, not a Docker, Dokploy or image requirement. It was retired after reviewing actual limits, measurements and host pressure. Evaluate the full capped task against current headroom, recent OOM events and memory stalls; do not use that old threshold as a permanent recovery blocker. Reservations constrain scheduling but do not prevent other unbounded applications from consuming more memory.

## Future releases and containment

1. Build and qualify off the shared VPS, using a clean intended source revision. Do not rebuild this recovered image simply because the source commit was pushed.
2. Publish privately, record the digest and configure registry authentication without placing tokens in source or logs. Retain and verify the controls above.
3. Serialize the complete release, including its observation period. Check running tasks and queued deployments before starting. Use an application-specific release lock; manual UI deploys do not honor an SSH lock automatically.
4. Preserve one replica and stop-first replacement. Follow startup logs and events; verify public readiness, catalogue, auth and voice checks, then observe for at least ten minutes.
5. On failed startup, OOM, task churn or severe host pressure, contain only the backend to zero and preserve logs. Save the zero-replica hold in Dokploy too. Do not blindly roll back an entire previous service specification, which may restore unsafe settings.

Historical full-file source patches remain in Dokploy but are bypassed by Docker-image deployment. Before ever switching back to source builds, reconcile them so they cannot overwrite newer code. Do not prune Docker, remove persistent data, restart the daemon or modify unrelated deployments as a routine recovery step.

References: [Docker resource constraints](https://docs.docker.com/engine/containers/resource_constraints/), [Swarm service configuration](https://docs.docker.com/engine/swarm/services/).
