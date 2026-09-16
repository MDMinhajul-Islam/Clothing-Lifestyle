# NexGen VPS overload: inspection and proposed recovery

## New evidence from the supplied terminal transcript

All five backend names contain `.1.` followed by different task IDs. This identifies overlapping generations of **slot 1**, rather than five ordinary replica slots:

| Container | Task ID |
| --- | --- |
| 7dac63d34842 | j73c4j4jf52vtsr1xnuu0zsu2 |
| 52a135fdc8c3 | r9xc1mgvv6qdrir0ia08toqfv |
| f97fe160c2b2 | h61x9lre99jujepse3xios10h |
| 9e5e196f12a5 | 84fkpo5d9fkmdeki3k9hb35bw |
| 1f8681881874 | w0q5dpz7e8f3q3nk291890t84 |

All five reported `Up 9 minutes (health: starting)`. This is not explained by the source Dockerfile's 60-second start period alone. Effective health overrides, missing/delayed health execution, daemon reconciliation or incomplete task shutdown remain to inspect. Each task had only 2–5 PIDs in that stats sample; this does not demonstrate a large PyTorch thread pool. The exact startup stage is still unknown.

Combined sampled backend CPU was **173.53%**, approximately 1.74 logical CPUs under Docker's usual Linux accounting. The five sampled memory usages sum to approximately **1,078 MiB**. These measurements support substantial active NexGen load but do not establish that these containers alone caused the earlier 3.7 GiB memory peak or the entire load average. `top -b -n 1` is not a sustained interval profile.

At 04:07, `free` reported only **82 MiB available**; at 04:12, `top` reported approximately **2,262 MiB available**, while CPU idle remained zero. Thus memory pressure was intermittent; constant memory exhaustion is not proven. Kernel OOM/restart history is needed. The login MOTD was dated the previous day and is stale; its load 0.38 must not be used as a current-health measurement.

The supplied `docker service ls` and health inspect were interrupted. `docker pause` was also interrupted with no successful result, and the subsequent container list did not show Paused. Do not assume that pause succeeded or failed for every container: inspect `.State.Paused`. The last command, `docker service update --force dokploy`, has no supplied result. It targets the management service, not NexGen; do not repeat it as a NexGen recovery step.

Several other containers show indications of recent starts, and the NexGen frontend was also Up 9 minutes. A broader daemon/node/container restart or reconciliation event is a possibility requiring timeline evidence. The current transcript is insufficient to attribute the accumulation solely to the application health check or start-first policy.

## Status and evidence boundary

No service changes, rebuilds, container stops, deletions, pruning, Docker restarts, or changes to other applications were performed in this inspection. Three fresh SSH attempts timed out during banner exchange before authentication. The live Swarm specification, task history, health logs and process state could not be retrieved. The exact mechanism producing five simultaneous tasks remains **unconfirmed**. Do not redeploy on the overloaded VPS yet.

User-reported server evidence: Ubuntu 24.04; disk approximately 24% used; load approximately 108/100/98; 0% CPU idle; memory approximately 3.7/3.8 GB with no swap; at least five active NexGen backend containers, each health `starting`, consuming approximately 22%, 36%, 51%, 38%, and 25% CPU. Other applications had comparatively low CPU. These observations strongly implicate concurrent NexGen startup workloads in saturation. Memory availability, reclaim pressure and OOM kills still need kernel/process evidence; used memory alone does not establish an OOM event.

Earlier independently observed evidence: the backend service had 0/1 replicas because its image was missing. An initial rebuild restored an image, but startup failed with the Python 3.11 f-string SyntaxError. The patched deployment was observed applying two file overrides; completion of that image build and the image IDs now running have not been verified. Historical 0/1 is not proof of the current replica setting.

## Answers to the requested questions

| Question | What is established / what remains to prove |
| --- | --- |
| Why multiple tasks remained running | Not established. Compare exact Swarm service IDs, task slots, desired states, actual states, creation/start timestamps and image IDs. Multiple slots can mean multiple desired replicas; repeated same-slot tasks with predecessors desired Shutdown can indicate delayed cleanup/replacement. Similar names alone are insufficient. |
| Why all stayed health starting | No successful health probe is established for these containers. Each backend initializes a DB pool, imports/loads the embedding model and runs a warmup before FastAPI startup completes. Resource starvation can delay that sequence. Fresh replacements, health overrides or delayed probe execution also fit the snapshot. Read effective health configuration and per-container probe history. |
| Update/restart strategy caused overlap | Unknown until Spec.UpdateConfig, RollbackConfig, TaskTemplate.RestartPolicy, StopGracePeriod and UpdateStatus are read. Start-first permits temporary overlap, but by itself does not explain five persistently active tasks for one desired replica. |
| Restart/update loop | Plausible, not proven. Repeated task creation/failure timestamps, exit/error/health events and service version changes distinguish task replacement from repeated Dokploy deployments. A replacement loop does not imply Docker image builds are repeating. |
| What changed | Git commit f2ba6d7 changes only email regex evaluation placement and adds python -m compileall -q backend during image build. It does not change the health check, process command, dependency declarations, model warmup or Swarm policies. The prior missing image cannot provide a binary baseline. Floating base image and transitive dependencies can differ on rebuild despite unchanged source. The previous genuinely working image/version has not been identified. |
| Health endpoint/configuration failing | Configured Dockerfile probe is localhost:8000/health, urllib timeout 5s, Docker timeout 10s, interval 30s, start-period 60s, retries 3. /health executes SELECT 1 through the DB pool. The route is unavailable until startup completes. Actual failure mode (refused, timed out, 500, failed DB, no scheduled probe) is not yet observed. Live service overrides may replace these defaults. |
| One or multiple replicas | Earlier 0/1 observed; current requested count unknown. Inspect Spec.Mode.Replicated.Replicas. Active container count does not equal desired replica count. |
| Swarm recreating unhealthy tasks | Requires task history and health events. Inspect RestartPolicy and task Status.Err; container RestartCount alone misses Swarm replacement because replacements have new container IDs. |

## Source inspection

- `Dockerfile`: one uvicorn process; no workers flag. Health probe as above. Build installs CPU PyTorch and caches MiniLM. Compileall runs during build, not each container startup, and does not execute/import the model.
- `backend/app/main.py:30`: lifespan calls init_db_pool, initialize_embedding_client, then embed for a startup warmup before yielding.
- `backend/app/rag/embeddings.py:89`: imports torch and sentence_transformers, loads MiniLM with local_files_only=True. Process-local cache means each task owns its own model. No explicit torch thread limit appears here.
- `backend/app/api/routes_meta.py:12`: /health requires the database and SELECT 1. A DB outage can make the health check fail even if the HTTP server is otherwise alive.
- `backend/app/db.py`: initializes the configured connection pool. Defaults are two minimum and ten maximum connections per process, but live overrides remain uninspected.

Working hypothesis: simultaneous model startups consume CPU and memory, delay readiness/probes, and possibly trigger further task replacement, amplifying pressure. This is not an exact RCA until service/task/health evidence confirms every link. Stuck task termination, replica misconfiguration, concurrent updates and OOM are alternatives still open.

## Read-only inspection commands (Ubuntu SSH session)

Run the small service queries first; keep the existing SSH session open. Do not dump full service/container inspect output because it can contain secrets. The following templates intentionally omit environment values.

```sh
svc=nexgenclothing-lifestyle-nexgenbackend-tok2fu
date -u
uptime
free -m
docker service inspect "$svc" --format '{{json .Spec.Mode}} {{json .Spec.UpdateConfig}} {{json .Spec.RollbackConfig}} {{json .Spec.TaskTemplate.RestartPolicy}} {{json .Spec.TaskTemplate.Resources}} {{json .UpdateStatus}}'
docker service inspect "$svc" --format 'Version={{.Version.Index}} Updated={{.UpdatedAt}} Image={{.Spec.TaskTemplate.ContainerSpec.Image}} Health={{json .Spec.TaskTemplate.ContainerSpec.Healthcheck}} StopGrace={{json .Spec.TaskTemplate.ContainerSpec.StopGracePeriod}}'
docker service ps --no-trunc "$svc"
docker ps -a --filter "label=com.docker.swarm.service.name=$svc" --format '{{.ID}} {{.Names}} {{.Status}} {{.Image}}'
```

For each exact container ID returned, substitute it below. Do not run repeated stats polling or manually execute extra model imports under overload.

```sh
docker inspect CONTAINER_ID --format 'Service={{index .Config.Labels "com.docker.swarm.service.id"}} Task={{index .Config.Labels "com.docker.swarm.task.id"}} Image={{.Image}} Created={{.Created}} Started={{.State.StartedAt}} PID={{.State.Pid}} OOM={{.State.OOMKilled}} Exit={{.State.ExitCode}} Health={{json .State.Health}} EffectiveProbe={{json .Config.Healthcheck}}'
docker logs --timestamps --tail 60 CONTAINER_ID
docker top CONTAINER_ID -eo pid,ppid,stat,pcpu,pmem,nlwp,comm
```

Review logs locally and redact customer data, tokens, URLs containing credentials and request bodies before sharing. Useful startup milestones are DB pool initialization, embedding-model initialization, warmup completion and application startup complete. Preserve task errors and health probe output.

```sh
vmstat 1 5
ps -eo pid,ppid,stat,pcpu,pmem,nlwp,comm --sort=-pcpu | head -25
journalctl -k --since '-2 hours' --grep 'Out of memory|Killed process|oom' --no-pager -n 30
```

The process listing helps separate remaining build processes from running backend processes; vmstat distinguishes run-queue pressure, blocked tasks, CPU idle and I/O wait. Dokploy deployment history/log timestamps should then be matched with service UpdatedAt and task CreatedAt. Inspect the previous service spec/image IDs without printing Env; determine whether rollback points at a usable image rather than the already-proven broken image.

## Proposed recovery commands — NOT executed

First capture the small service/task/health evidence above. Confirm the exact service is replicated and its mounts; stopping tasks loses in-memory calls and may discard ephemeral container filesystem state, but does not delete mounted volumes or external databases. Pause/cancel only an identified active NexGen deployment in Dokploy, if one exists, so it cannot immediately reapply the desired replica count. Do not kill generic buildkit or Docker processes.

For urgent containment, the smallest reversible scheduler-level action is:

```sh
docker service scale --detach=true nexgenclothing-lifestyle-nexgenbackend-tok2fu=0
```

This requests shutdown of only this service's replicas and removes the desired workload that Swarm would otherwise replace. It does not delete the service, images or volumes. It intentionally keeps NexGen unavailable while protecting the other applications. It does not cancel an independently running image build. Scaling down can take time; do not repeatedly stop individual containers while Swarm still desires replacements.

Verify actual convergence:

```sh
docker service ps --no-trunc nexgenclothing-lifestyle-nexgenbackend-tok2fu
docker ps --filter label=com.docker.swarm.service.name=nexgenclothing-lifestyle-nexgenbackend-tok2fu
vmstat 1 5
free -m
uptime
```

If containers remain active after desired state Shutdown, inspect their exact PIDs, D-state and Docker shutdown errors before proposing targeted termination. Do not escalate to deleting containers or restarting Docker blindly. CPU idle and available memory should recover before load averages fully decay; 5/15-minute load remains elevated after the active problem stops.

Only after confirming the cause, image identity/fix, host headroom and zero remaining NexGen containers, a controlled one-instance diagnostic trial can use the existing image with automatic retries temporarily disabled:

```sh
docker service update --detach=true --replicas 0 --update-order stop-first --update-parallelism 1 --update-failure-action pause --rollback-order stop-first --restart-condition none nexgenclothing-lifestyle-nexgenbackend-tok2fu
docker service scale --detach=true nexgenclothing-lifestyle-nexgenbackend-tok2fu=1
```

These are conditional trial commands, not instructions to run immediately or permanent availability policy. They do not rebuild or select a different image. Set measured CPU/memory limits before the trial if required by the recovered host's headroom; do not guess a memory cap that repeatedly OOM-kills the model. After proving stable health, choose bounded restart backoff and persist the approved settings in Dokploy, which may otherwise overwrite manual Swarm changes on deployment. Do not disable health checks, blindly extend their grace period, or roll back to an unverified broken image.

## Recovery acceptance

Exactly one active NexGen backend task, effective desired replicas one, stable container ID/no replacement churn, health healthy with successful probes, /health HTTP 200, completed startup warmup, memory headroom and nonzero CPU idle under normal load. Verify catalogue, login and Retell separately. Confirm the other services retain their prior desired configuration and availability. Monitor longer than the effective startup/health/restart window; a transient 1/1 snapshot is insufficient.

## References

- Docker HEALTHCHECK semantics: https://docs.docker.com/reference/dockerfile/#healthcheck
- Swarm service update/restart options: https://docs.docker.com/reference/cli/docker/service/update/
- Scaling one service to zero preserves its service definition: https://docs.docker.com/reference/cli/docker/service/scale/

No claim of host stabilization or exact overlap root cause is made until live evidence is available.
