# Knowledge transfer / handover checklist (M10)

For L1/L2 support picking this up after the capstone. Written as it would read for a real
handover, even though this build has one author, not an outgoing team — see
[production-readiness.md § Support contacts](./production-readiness.md#support-contacts-and-escalation)
for how the escalation tiers below map onto that reality.

## Repos and access

- **Code**: this repository. Branch policy: `develop` is the integration branch; each milestone
  landed as `feature/M<N>-*` merged into `develop`. No `main` branch promotion has happened yet
  in this build.
- **No external accounts exist to hand over** — no real AWS account, no LLM API key, no Splunk
  instance, no GitLab/GitHub CI runner was ever provisioned for this build (see
  [known-issues.md § No real external dependency was ever exercised live](./known-issues.md)).
  Whoever picks this up for real production use provisions these fresh; there is nothing to
  rotate or inherit.

## URLs (local dev — there is no deployed environment)

| Service | URL | Health check |
| --- | --- | --- |
| mortgage-service | http://localhost:8080 | `GET /actuator/health/readiness`, `/liveness` |
| servicing-service | http://localhost:8081 | `GET /actuator/health/readiness`, `/liveness` |
| analytics-service | http://localhost:8000 | `GET /health` |
| ai-assistant | http://localhost:8001 | `GET /health` |
| LocalStack | http://localhost:4566 | `GET /_localstack/health` |

Start everything: `docker compose up --build -d` from the repo root. Full startup/health-check
sequence: [runbook.md](./runbook.md).

## Credentials (dev/test only — see `database/README.md`, never real secrets)

All five seeded `app_user` rows share the password `Capstone#2026`:
`admin@capstone.local` (ADMIN), `underwriter@capstone.local` (UNDERWRITER),
`servicing@capstone.local` (SERVICING_AGENT), `risk@capstone.local` (RISK_ANALYST),
`support@capstone.local` (SUPPORT). `JWT_SECRET` is set in `docker-compose.yml`
(`compose-dev-only-shared-jwt-secret-never-use-outside-this-stack`) and shared identically across
all three services that validate tokens — rotating it anywhere requires rotating it everywhere
(`runbook.md § Secrets rotation`).

## On-call / escalation

No real on-call roster exists for a capstone build. If this goes into real use:

1. **L1** triages against [runbook.md](./runbook.md) first — health checks, common failure modes
   (Postgres connection, LocalStack/AWS connectivity, JWT_SECRET mismatch — the exact class of bug
   found and fixed this milestone, see [known-issues.md](./known-issues.md)).
2. **L2** escalation targets are the "Owner" column in
   [docs/security/risk-register.md](../security/risk-register.md) — each open risk already names
   the component maintainer responsible.
3. **SME**/architecture questions: [docs/adr/](../adr/) for the "why", and
   [docs/architecture/](../architecture/) for the "what".
4. **Active incident**: [incident-response.md](./incident-response.md) for the process,
   [rca-template.md](./rca-template.md) for the writeup format,
   [rca-2026-10-28.md](./rca-2026-10-28.md) for a real worked example from this build (the
   actuator health-probe path bug — found, triaged, fixed, and documented inside one milestone).

## Splunk queries L1/L2 would actually run

Never validated against a live Splunk instance in this build (see `slo.md`'s own caveat) — these
are the real saved searches in [monitoring/splunk/searches.spl](../../monitoring/splunk/searches.spl),
listed here so L1/L2 don't have to go find the file during an incident:

```spl
# Trace one request across services by correlation ID
index=mortgage_dev correlationId="<id from an error response>"
| sort _time

# Error rate, last hour, by service
index=mortgage_dev level=ERROR earliest=-1h
| stats count by service

# Payment API p95 latency (SLO: < 500ms — slo.md)
index=mortgage_dev service=mortgage-service path="/api/v1/mortgages/*/payments" method=POST earliest=-5m
| stats p95(durationMs) as p95_latency_ms
```

The dashboard (`monitoring/splunk/dashboard.xml`) and the payment-latency alert
(`monitoring/splunk/alert-payment-latency.json`, fires at p95 > 500ms over two consecutive
5-minute windows) are real Simple-XML/alert-JSON artifacts, syntactically valid, never fired
against a live instance.

## What breaks and how to tell (quick-reference, full detail in runbook.md)

| Symptom | Likely cause | Where to look |
| --- | --- | --- |
| mortgage-service won't start | Postgres not healthy yet, or `JWT_SECRET` unset outside dev/test (fails fast by design — `JwtService`) | `docker compose logs mortgage-service` |
| ai-assistant returns 401 for a token that looks valid | JWT signing-algorithm mismatch — exactly the bug found and fixed this milestone; confirm `JWT_SECRET` matches *and* check the token header's `alg` is `HS256` | [known-issues.md](./known-issues.md) |
| `tests/e2e` fails with `429 RATE_LIMITED` on a login step | Too many logins within 60s against mortgage-service's `RateLimitFilter` (10 req/60s) — restart mortgage-service to clear its in-memory limiter state, or wait | [known-issues.md](./known-issues.md), `tests/e2e/README.md` |
| analytics-service integration tests fail on seed-count assertions | Something else (often `tests/e2e`'s onboarding journey) wrote real rows into the shared dev Postgres since the last reset | `database/scripts/reset-dev-db.sh`, [test-strategy.md § Local test-isolation note](./test-strategy.md) |
| `terraform apply` fails on an ECS resource | LocalStack Community doesn't support ECS (Pro-only) — the `compute` module is gated off by default (`enable_compute = false`) | `infrastructure/terraform/README.md` |

## Final release

Tagged `v1.0.0-capstone` on `develop` once this milestone merges — see
[production-readiness.md](./production-readiness.md) for the go-live recommendation this tag
represents sign-off on.
