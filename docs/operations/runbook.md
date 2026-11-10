# Operations runbook

General operational procedures. Messaging-specific operations (SNS/SQS/DLQ):
[messaging-runbook.md](./messaging-runbook.md). CI/CD security controls:
[devsecops-baseline.md](./devsecops-baseline.md).

## Startup (M10)

```bash
docker compose up --build -d postgres db-init mortgage-service servicing-service analytics-service ai-assistant
```

`db-init` runs the migrations + seed scripts once and exits 0 — every other service's
`depends_on: db-init: condition: service_completed_successfully` waits for that, not just for
Postgres to accept connections. Confirm everything is actually ready (container "running" is not
the same as "ready" for a Spring Boot app doing JPA schema validation at startup):

```bash
for i in $(seq 1 30); do
  curl -sf http://localhost:8080/actuator/health/readiness \
    && curl -sf http://localhost:8081/actuator/health/readiness \
    && curl -sf http://localhost:8000/health \
    && curl -sf http://localhost:8001/health && break
  sleep 3
done
```

LocalStack (`localstack`, `localstack-init`) is a dependency of the Java services regardless of
whether you listed it explicitly — `docker-compose.yml`'s `depends_on` pulls it in. First boot on
a machine without the images cached takes longer (Lambda deploy inside `localstack-init` zips and
registers a function — see `infrastructure/aws/lambda/doc-processor/deploy-local.sh`).

**Full reset** (wipe and reseed the database — safe, same idempotent scripts CI uses):
```bash
POSTGRES_HOST=localhost POSTGRES_OWNER_PASSWORD=<see docker-compose.yml POSTGRES_OWNER_PASSWORD> \
  bash database/scripts/reset-dev-db.sh
```

## Deploy (M9/M10)

See [cicd.md § Deploy](./cicd.md#deploy) for the three deploy jobs
(`deploy_dev`/`deploy_test`/`deploy_prod_plan`) and exactly what "deployed" means in this build
(image pushed to the registry, tagged with the commit SHA — there is no persistent dev/test
cluster provisioned to run it on; `docker-compose.yml` is the standing substitute for that).
Releases are tagged on `develop`/`main` per the capstone policy
(`git tag -a v1.0.0-capstone -m "Final capstone submission"`) — see
[production-readiness.md](./production-readiness.md) for the go-live sign-off a tag represents.

## Common failures (M10)

| Symptom | Cause | Fix |
| --- | --- | --- |
| mortgage-service/servicing-service exit immediately on startup | `JWT_SECRET` unset/default outside a `dev`/`test` profile — fails fast by design (`JwtService`/`JwtValidationService`, R-2 in the risk register) | Set `JWT_SECRET` to a real value, or confirm `SPRING_PROFILES_ACTIVE` is `dev`/`test` for local work |
| A Java service hangs on startup, never reports healthy | Postgres not actually ready yet, or `db-init` hasn't completed — check `docker compose logs db-init` finished with exit 0 | `docker compose ps` to check `db-init`'s exit code; re-run `docker compose up -d` once Postgres is healthy |
| ai-assistant rejects a token that looks valid (401) | JWT signing-algorithm mismatch between the issuer and validator — see [known-issues.md](./known-issues.md) for the exact bug found and fixed this milestone | Confirm the token's header `alg` is `HS256`; confirm `JWT_SECRET` is byte-for-byte identical across all three services |
| `terraform apply` fails on an ECS resource ("not yet implemented or pro feature") | LocalStack Community doesn't support ECS | Expected — the `compute` module is gated off by default (`enable_compute = false`); see `infrastructure/terraform/README.md` |
| `tests/e2e` fails with `429 RATE_LIMITED` on a login step | mortgage-service's `RateLimitFilter` (10 req/60s/IP) tripped by the suite's own repeated logins | Restart `mortgage-service` to clear its in-memory limiter state (or wait 60s) — `tests/e2e` now caches tokens per role for exactly this reason |
| Local host port 5432 conflicts with a native Postgres install | A Homebrew/system Postgres already bound to `5432` | Query the compose container directly: `docker exec mortgage-intelligence-platform-postgres-1 psql -U mortgage_app -d mortgage_intel` |

## Secrets rotation (M6)

Secrets in this platform today: `POSTGRES_PASSWORD` / `POSTGRES_OWNER_PASSWORD` (database roles,
[database/README.md](../../database/README.md)), `JWT_SECRET` (shared HS256 signing key between
`mortgage-service` and `servicing-service`), and AWS credentials (none in production yet —
LocalStack locally, IAM role in a real deployment).

**Approach:**

1. **Never rotate by editing a running container's env var alone** — the old value must stop
   working everywhere at (roughly) the same time, or you get a window where both old and new
   secrets are simultaneously valid or where some instances reject requests the others accept.
2. **`JWT_SECRET` rotation** has a hard constraint specific to this platform: both
   `mortgage-service` and `servicing-service` must be updated to the *same* new value before
   either restarts, because `servicing-service` validates tokens with no inter-service call to
   mortgage-service (ADR-002). A staggered rotation causes every in-flight token minted under
   the old secret to fail validation the moment one service restarts with the new one — there is
   no overlap/grace period in the current design. Plan rotation as: issue new secret → update
   both services' env configuration → restart both together → confirm with a login + protected
   call (same check as `docs/security/security-controls.md`) → done. Existing tokens are
   invalidated; clients must re-login (the TypeScript client in
   `clients/mortgage-api-consumer/` already handles this via its re-login-on-401 path).
3. **Database password rotation:** update the password via `ALTER ROLE mortgage_app WITH
   PASSWORD '...'` as a superuser, update `POSTGRES_PASSWORD` in each service's environment, and
   restart. `mortgage_owner` (DDL) rotates the same way, independently, since migrations don't
   run continuously.
4. **If a secret was exposed** (committed to Git, logged, pasted somewhere public): treat it as
   compromised and rotate immediately per the steps above — do not wait for a scheduled rotation
   window. See [devsecops-baseline.md § If a secret is committed](./devsecops-baseline.md#if-a-secret-is-committed).
5. **No scheduled rotation cadence is enforced yet** (no secrets manager / rotation automation in
   this capstone build). A real deployment should put secrets in a managed store (AWS Secrets
   Manager / Parameter Store) with automatic rotation; out of scope for M6, tracked for M8/M9.

## Rollback (M9)

Pipeline: [cicd.md](./cicd.md). Images are pushed tagged with the commit SHA
(`$CI_REGISTRY_IMAGE/<service>:$CI_COMMIT_SHORT_SHA>`), never `:latest` — that's what makes
rollback a known-good re-deploy rather than a guess.

1. **Identify the last known-good SHA.** Check the deploy stage's pipeline history for the most
   recent successful `deploy_test` (or `deploy_dev`) run before the bad one, and note its
   `$CI_COMMIT_SHORT_SHA`.
2. **Re-deploy that tag**, not a new build from a reverted commit — rebuilding can pick up an
   unrelated dependency update between now and then. Re-run the `deploy_*` job for the known-good
   SHA (GitLab: "Retry" on that specific historical job, or manually `docker pull`/redeploy that
   tag in the target environment).
3. **Database migrations are forward-only in this project** (`database/README.md`: "Never edit a
   merged migration; add `003_*.sql`"). A rollback that needs an old migration undone requires a
   new migration that reverses it — there is no automatic `migrate down`. Check whether the bad
   deploy included a migration before assuming a pure image rollback is sufficient.
4. **JWT_SECRET rotation and rollback don't mix well** — if the bad deploy also rotated
   `JWT_SECRET` (see "JWT_SECRET rotation" above), rolling back the image alone leaves the new
   secret in place and all tokens from before the rotation still invalid. Roll back the secret
   too, in the same step, not as an afterthought.
5. **Verify after rollback**: health checks on both Java services, then the same login +
   authenticated GET check `integration_test` runs in CI (`docs/operations/cicd.md`), against
   the rolled-back environment specifically.

## Incident response

See [incident-response.md](./incident-response.md) for the escalation path during an active
incident, and [slo.md](./slo.md) for the SLOs an incident might be breaching.
