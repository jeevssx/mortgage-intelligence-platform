# Splunk artifacts (M9)

No Splunk instance (HEC URL/token) was available in this build environment — see
[docs/operations/slo.md](../../docs/operations/slo.md) "Splunk ingestion status" for the same
honesty note applied to no-real-AWS-account (M8) and no-LLM-API-key (M7) elsewhere in this repo.
These are real Splunk artifact formats, written to be imported directly into a real Splunk
instance, but **not independently verified against one** — there's no instance to import them
into and confirm.

## Files

| File | Splunk artifact type | Import as |
| --- | --- | --- |
| `searches.spl` | Saved search queries (one per SLI in `docs/operations/slo.md`) | `Settings → Searches, reports, and alerts → New`, paste the query |
| `dashboard.xml` | Simple XML dashboard: request rate, 5xx rate, payment API p95 latency, DLQ depth | `Settings → Dashboards → New Dashboard → Source` |
| `alert-payment-latency.json` | Saved search + alert action, `savedsearches.conf`-equivalent fields in JSON for readability | `Settings → Searches, reports, and alerts → New Alert`, map each field |

## Index naming

`mortgage_dev` (per the milestone spec's example) — every search in `searches.spl` assumes
`index=mortgage_dev`. A real deployment would also have `mortgage_test`/`mortgage_prod`; the
queries are identical modulo the index name.

## HEC forwarding (not wired up)

Each service already emits structured JSON to stdout (`guides/standards.md`). The remaining
step for real ingestion — not done here, no endpoint to send to — is either:

- A Splunk Universal Forwarder or the Docker logging driver pointed at HEC, reading each
  container's stdout, or
- Each service's `JsonFormatter`/`logback` config additionally POSTing to
  `$SPLUNK_HEC_URL/services/collector` with `Authorization: Splunk $SPLUNK_HEC_TOKEN` — a small
  addition to `src/utils/logging_config.py` (Python services) and a logback HEC appender (Java
  services), not built here since there's nothing to send to.
