# Production readiness (M10)

Every checklist item below links to the actual evidence (a doc, a test class, a live command run
for this milestone) rather than a bare checkbox — per this milestone's own "common mistakes"
guidance ("Readiness checkbox without evidence").

## Checklist

- [x] **Functional validation** — unit/API tests passing in all four services (30 + 33 + 79 + 16
      tests; see [test-strategy.md](./test-strategy.md) for the exact counts and coverage), plus
      all five E2E journeys passing live (`tests/e2e`, 12 scenarios/54 steps).
- [x] **Security validation** — closed against the M6 risk register; see "Security validation
      closure" below.
- [x] **Performance validation (smoke)** — see "Performance smoke" below. Baseline only, not a
      load test, per this milestone's explicit scope ("not full load test unless required").
- [x] **CI/CD validation** — `.gitlab-ci.yml`/`.github/workflows/ci.yml` stages verified locally
      (every command each job runs has been executed directly on this machine — see
      [cicd.md](./cicd.md)); the `e2e_test`/`e2e-test` stage specifically found and fixed two real
      bugs before merge (see "Known issues" below). **Caveat, stated plainly**: neither pipeline
      has been run against a live GitLab/GitHub Actions runner in this build — no such runner is
      available here, the same category of gap as no real AWS account (M8) or LLM key (M7).
- [x] **Infrastructure validation** — Terraform modules apply cleanly against LocalStack
      (`infrastructure/terraform/environments/dev`); `prod`/`test` environments' real-AWS backend
      is syntactically valid and `terraform plan`-able but never `apply`d (no AWS account — see
      [infrastructure/terraform/README.md](../../infrastructure/terraform/README.md)).
- [x] **Monitoring validation** — SLI/SLO defined with concrete thresholds, Splunk dashboard/
      saved-search/alert artifacts are real and valid JSON ([slo.md](./slo.md)); never validated
      against a live Splunk instance (none available) — stated there, not hidden here.
- [x] **Backup/recovery considerations** — documented in [runbook.md](./runbook.md): Postgres is
      the system of record (DynamoDB is a derived, rebuildable cache — see ADR in
      `docs/architecture/`); no automated backup job exists in this build (local/LocalStack dev
      stack has no persistent-prod target to back up). Recorded as a residual risk below, not
      silently skipped.
- [x] **Rollback procedure tested** — see "Rollback, actually exercised" below. This is the one
      item on this list that got a live dry run, not just a written procedure.
- [x] **Runbook complete** — [runbook.md](./runbook.md): secrets rotation, rollback, incident
      response.
- [x] **Known issues documented** — [known-issues.md](./known-issues.md).
- [x] **Risk register updated** — [docs/security/risk-register.md](../security/risk-register.md)
      re-reviewed this milestone; no new Critical/High findings. Residual risks carried into the
      go-live recommendation below.
- [x] **Go-live recommendation signed by team** — see "Go-live recommendation" below. (Solo
      build — "signed by team" is the author's own sign-off; see note there.)

## Security validation closure

Re-reviewed [docs/security/risk-register.md](../security/risk-register.md) against the current
codebase (not just re-read — re-verified R-1/R-2 are still closed by running `RbacTest` and
`JwtServiceTest`/`JwtValidationServiceTest` live, all passing, this milestone):

| ID | Status | Notes |
| --- | --- | --- |
| R-1 | **Closed** | `@PreAuthorize` denials return 403/401 correctly (not 500) — re-verified. |
| R-2 | **Closed** | Insecure default JWT secret fails fast outside dev/test — re-verified. Also found and fixed a *related, previously unknown* bug this milestone: the issuing side signed HS384 (JJWT auto-selecting by key length) while ai-assistant's validator hardcoded HS256, silently rejecting every real end-to-end token since M7. Pinned HS256 explicitly; see the JWT fix commit and [known-issues.md](./known-issues.md). |
| R-3 | Open, accepted | Rate limiting is login-only, in-memory, single-instance. No change this milestone — still Medium/Medium, still tracked, no committed remediation date. |
| R-4 | Open, accepted | No message-level authenticity check on SNS/SQS. Unchanged. |
| R-5 | Open, accepted | External IDs reflected verbatim in error messages. Unchanged, cosmetic. |
| R-6 | Partially closed, accepted | Framework CVEs (9 Critical/43 High at last scan) — see "Vulnerability re-scan" below for the current count. |

**No new Critical/High findings originating in project code** were introduced since M6. The
three open items (R-3/R-4/R-5) remain Medium/Low and explicitly acceptable to carry into
production per the remediation backlog's own reasoning — they are not blocking go-live.

### Vulnerability re-scan

Re-ran Trivy against a freshly built `mortgage-service` image (same command CI's
`sca`/`container_scan` stages use; the other three images weren't re-scanned individually for
this document since the category of finding — Spring Framework/Tomcat/Netty, shared across all
four Spring/FastAPI images via the same base layers — is the same):

```bash
docker build -f docker/Dockerfile.mortgage-service -t mortgage-service:readiness-check .
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest \
  image --scanners vuln --severity HIGH,CRITICAL --format json mortgage-service:readiness-check
```

**Result: 9 Critical, 43 High** — identical to the M9 scan already recorded in the risk register.
No new Critical/High finding traceable to this project's own code since M9. **Exception
record**: R-6 is carried forward as an accepted risk requiring a Spring Boot 4.x major-version
upgrade to fully close; tracked with an owner in the risk register, not waived silently.

## Performance smoke

Baseline latency, single-machine docker-compose stack (not a dedicated perf environment — results
are indicative, not a formal SLO certification). Measured live for this document:

| Endpoint | Requests | p50 | p95 | Notes |
| --- | --- | --- | --- | --- |
| `GET /api/v1/mortgages/{id}` (mortgage-service) | 20 sequential | 6.2ms | 20.7ms | |
| `GET /api/v1/mortgages/{id}` (mortgage-service) | 50 @ concurrency 10 | 20.0ms | 37.8ms | 50/50 returned 200 |
| `GET /api/v1/mortgages/{id}/delinquency` (servicing-service) | 20 sequential | 5.8ms | 61.4ms | |
| `POST /api/v1/mortgages/{id}/payments` (mortgage-service) | 15 sequential | 16.1ms | 69.7ms | 15/15 returned 201. **SLO target (slo.md): p95 < 500ms — met with ~7x headroom.** |
| `POST /api/v1/assistant/ask` (ai-assistant, TF-IDF + extractive) | 10 sequential | 3.0ms | 10.6ms | No LLM API call — in-process retrieval only; a real OpenAI-backed call would add network latency not reflected here. |

No full load test was run (explicitly out of scope per this milestone — "Unlimited performance
tuning" is also out of scope). These numbers establish a baseline for future regression
comparison, not a capacity claim for a specific production traffic volume.

## Rollback, actually exercised

[runbook.md § Rollback](./runbook.md#rollback-m9) documents the procedure (redeploy the last-good
commit-SHA-tagged image, never `:latest`). Dry-run performed for this milestone, against the
local stack (standing in for the deploy-stage rollback since no live registry/runner is
available):

1. Checked out the commit immediately before the HS256 fix (`e9f620e`, via an isolated
   `git worktree` so the real working tree was never touched) into a scratch build, ran it
   alongside the live stack, and confirmed the regression reproduces: its token's header is
   `{"alg":"HS384"}` and the live (fixed) ai-assistant rejects it with 401.
2. Rolled forward: the same login against the current, already-running `mortgage-service`
   issues `{"alg":"HS256"}` and ai-assistant returns 200 for it — the same live check used to
   find the bug originally, now proving the fix and the rollback target both behave as expected.
3. Confirmed `database/scripts/reset-dev-db.sh` is idempotent and safe to re-run as part of a
   rollback that doesn't involve a migration (forward-only migrations — runbook.md note 3).

This exercises the *mechanics* of "roll back to a known-good artifact and re-verify" end to end;
it does not exercise GitLab's actual `deploy_*` job retry UI, which needs a live runner this
build doesn't have.

## Readiness dry run notes (Session 35)

Performed live, this milestone, 2026-11-04 (UTC), solo:

| Time (UTC) | Action | Result |
| --- | --- | --- |
| ~12:40 | Ran `tests/e2e` live against the full compose stack | 12/12 scenarios, 54/54 steps passing |
| ~12:45 | Re-ran `RbacTest`/`JwtServiceTest`/`JwtValidationServiceTest` (R-1/R-2 closure check) | All passing |
| ~12:50 | Performance smoke (sequential + concurrency-10 bursts, 4 endpoints) | See table above; SLO'd payment endpoint at 69.7ms p95 vs. 500ms target |
| ~13:00 | Trivy re-scan of a freshly built `mortgage-service` image | 9 Critical / 43 High — unchanged from M9 |
| ~13:01 | Rollback dry run (pre-fix build via isolated worktree → reproduce bug → roll forward → re-verify) | Reproduced and resolved as expected; scratch container/image/worktree cleaned up afterward |

No blocking finding came out of this dry run. The one new discovery (the HS256/HS384 mismatch)
was found and fixed *before* this dry run, while first building `tests/e2e` — this dry run is
the confirmation pass, not the discovery pass.

## Go-live recommendation

**Recommendation: GO, with conditions.**

This is a capstone build by a solo author, not a team — "signed by team" above is this author's
own sign-off, made honestly rather than fabricating a multi-person review that didn't happen.

**Conditions** (must happen before any real-money/real-borrower use, not before this capstone
submission):
1. A real AWS account, replacing every LocalStack-only component (S3/SNS/SQS/DynamoDB/Lambda,
   ECS once provisioned) — see `infrastructure/terraform/README.md`.
2. A real LLM API key if the AI assistant's grounded-answer quality needs to exceed the
   TF-IDF/extractive baseline — see `ai/mortgage-knowledge-assistant/README.md`.
3. A real Splunk (or equivalent) instance to validate the dashboard/alert artifacts actually fire
   as designed — see `slo.md`.
4. Multi-instance deployment needs the rate limiter backed by a shared store (R-3) before it's
   meaningful under horizontal scaling.

### Top 5 residual risks

| # | Risk | Owner | Why it's residual, not blocking |
| --- | --- | --- | --- |
| 1 | R-6: third-party framework CVEs (Spring/Tomcat/Netty) | Platform maintainer | Requires a Spring Boot 4.x major upgrade; non-reachable via this app's actual code paths per the risk register's own analysis. |
| 2 | R-3: login rate limit is in-memory/single-instance | mortgage-service maintainer | Fine for this build's single-replica deployment; needs Redis (or similar) before horizontal scaling. |
| 3 | No automated backup/restore job for Postgres (system of record) | Platform maintainer | No persistent-prod target exists in this build to back up; a real deployment needs this wired before go-live, not after. |
| 4 | R-4: no message-level authenticity check on SNS/SQS events | servicing-service maintainer | Requires access to the queue itself, which already has a network/IAM boundary; deferred, not ignored. |
| 5 | AI assistant's grounded-answer quality is TF-IDF/extractive only (no LLM key) | AI assistant maintainer | Deliberately degrades gracefully (insufficient-context + human-approval flag) rather than hallucinating; a real LLM key is a drop-in upgrade per the pluggable client design, not a rearchitecture. |

### Rollback pointer

[runbook.md § Rollback](./runbook.md#rollback-m9) — redeploy the last known-good
`$CI_COMMIT_SHORT_SHA`-tagged image; see "Rollback, actually exercised" above for the dry run
performed this milestone.

### Support contacts and escalation

Solo-author capstone build — there is no real on-call roster. The structure below is what
[kt-checklist.md](./kt-checklist.md) hands off, written as it would read for a real team:

- **L1 (first response)**: on-call engineer per the rotation this would use in production —
  checks [runbook.md](./runbook.md) first (health checks, common failures).
- **L2 (escalation)**: service maintainer named in the risk register's "Owner" column for the
  specific component involved.
- **SME (architecture/design questions)**: see `docs/adr/` for the reasoning behind each major
  decision; [incident-response.md](./incident-response.md) and
  [rca-2026-10-28.md](./rca-2026-10-28.md) for how the one real incident simulated in this build
  was triaged and fixed.
