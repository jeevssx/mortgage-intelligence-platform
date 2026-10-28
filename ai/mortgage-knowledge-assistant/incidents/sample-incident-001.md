# Incident log (synthetic) — sample-incident-001

**Reported:** 2026-02-14 09:12 UTC
**Reporter:** on-call engineer
**Affected service:** servicing-service

## Timeline

- 09:02 UTC — `servicing-service` `/actuator/health` starts returning 503 intermittently.
- 09:04 UTC — Correlation IDs in logs show `HikariPool-1 - Connection is not available` errors
  on roughly 1 in 5 requests.
- 09:06 UTC — Checked PostgreSQL: `pg_stat_activity` shows the connection count near
  `max_connections`; no single query is long-running.
- 09:09 UTC — Identified a recently deployed change increased request volume to
  `GET /api/v1/mortgages/{id}/servicing-history` roughly 4x due to a new polling client; the
  default Hikari pool size (10) was undersized for the new load.
- 09:12 UTC — Mitigated by bumping the connection pool size; 503s stopped within 2 minutes.
- 09:30 UTC — Root cause confirmed: pool exhaustion under increased polling load, not a database
  outage or a code defect in `servicing-service` itself.

## Impact

Approximately 18 minutes of intermittent 503s on `servicing-service` read endpoints. No data
loss — all requests either succeeded or failed cleanly with no partial writes, since the
affected endpoints are read-only.

## Follow-up actions

1. Raise the default Hikari pool size and document the sizing rationale relative to expected
   request volume.
2. Ask the polling client's owning team to reduce polling frequency or move to the SNS/SQS event
   backbone (`docs/architecture/event-catalog.md`) instead of polling.
3. Add a connection-pool-utilization alert so this is caught before user-visible 503s next time.
