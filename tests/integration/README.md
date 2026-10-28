# Integration tests

Multi-component tests that need a real database, message queue, or multiple live services —
distinct from the unit tests in `tests/unit/` (mocked dependencies) and the E2E journeys in
`tests/e2e/` (black-box, HTTP-only, no knowledge of internals).

- **CI `integration_test` stage** (`docs/operations/cicd.md`): brings up Postgres + LocalStack +
  both Java services via `docker-compose.yml` and runs a real login + authenticated GET —
  defined in `.gitlab-ci.yml`/`.github/workflows/ci.yml` directly rather than a separate script,
  since it's a handful of `curl` calls, not a test framework.
- **`database_migrations` CI job**: fresh PostgreSQL → roles → migrations → seed → idempotent
  re-apply → sample queries as the least-privilege role — the real integration test for the
  schema itself.
- **Analytics service's `INTEGRATION_DB=1` pytest marker**
  (`analytics/mortgage-analytics-service/tests/`): runs the same test suite against a real
  PostgreSQL connection instead of a mocked repository.
- **Manual live verification** throughout M4–M9's development (documented in each milestone's
  commit messages, e.g. the DynamoDB write-through check in the M8 `feat(servicing-service)`
  commit) — not automated here, but real runs against real LocalStack/Postgres, not assumptions.
