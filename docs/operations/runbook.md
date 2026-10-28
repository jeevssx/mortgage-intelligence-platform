# Operations runbook

General operational procedures. Messaging-specific operations (SNS/SQS/DLQ):
[messaging-runbook.md](./messaging-runbook.md). CI/CD security controls:
[devsecops-baseline.md](./devsecops-baseline.md).

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
