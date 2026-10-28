# SLI/SLO (M9)

## Service level indicators and objectives

| SLI | SLO target | Measurement |
| --- | --- | --- |
| Payment API success rate | 99.5% / 30 days | `count(status=201 or 400 or 404 or 409) / count(all requests)` on `POST /api/v1/mortgages/{id}/payments` — a 500 is the only outcome counted as a failure; a correctly-rejected 400/404/409 is the API working as designed, not an error |
| p95 payment API latency | < 500ms | p95 of request duration on `POST /api/v1/mortgages/{id}/payments`, measured end-to-end (includes the DB transaction and the SNS publish, which is fire-and-forget and logged-not-thrown on failure per ADR-002, so it should not add meaningful latency) |
| Servicing-history read availability | 99.9% / 30 days | `count(status != 500) / count(all requests)` on `GET /api/v1/mortgages/{id}/servicing-history` |
| SQS consumer lag | < 5 minutes | Time between an event's `occurredAt` and its `event_inbox.processed_at` — see `docs/architecture/event-catalog.md` |

These four are the ones with a defined alert (below). Error budget for the 99.5% payment success
target over 30 days: roughly 3.6 hours of fully-failed time, or a proportionally larger amount of
partial degradation — e.g. a 10% error rate for 36 hours burns the same budget.

## Measurement source

Every service already logs structured JSON with `correlationId`, `service`, and (for the Java
services) the HTTP status and duration via each request's access log line — see
`guides/standards.md` "Logging (structured)" and each service's `CorrelationIdFilter`/
`CorrelationIdMiddleware`. That's the raw signal these SLIs are computed from.

**Splunk ingestion status:** no Splunk instance (HEC URL/token) was available in this build
environment — the milestone spec calls these out as "instructor-provided," and none was
provisioned here, the same category of gap as no real AWS account (M8) or no LLM API key (M7).
What's real: the JSON log format Splunk would ingest (already in place since M3/M4), the saved
search queries that would compute these SLIs (`monitoring/splunk/`), and the dashboard/alert
definitions (`monitoring/splunk/dashboard.json`, `monitoring/splunk/alert-payment-latency.json`).
What hasn't been exercised: actually sending a log line to a Splunk HEC endpoint and confirming
it's searchable — there's no endpoint to send it to.

## Alert

**Payment latency alert** (`monitoring/splunk/alert-payment-latency.json`): fires when p95
payment API latency over a 5-minute window exceeds 500ms for two consecutive windows (avoids
alerting on a single slow request). Links to
[runbook.md](./runbook.md#rollback) and [incident-response.md](./incident-response.md) for the
response path. Severity maps to SEV2 per `incident-response.md`'s table.
