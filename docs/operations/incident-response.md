# Incident response (M9)

Escalation path and severity definitions. RCA template and examples:
[rca-template.md](./rca-template.md). SLOs an incident might breach: [slo.md](./slo.md).

## Severity levels

| Severity | Definition | Example | Response |
| --- | --- | --- | --- |
| SEV1 | A core API is down or data integrity is at risk for all users | `mortgage-service` 503s on every request; payment postings silently dropped | Page immediately, all hands, start an RCA timeline from the first alert |
| SEV2 | A core API is significantly degraded but partially functional | Payment latency p95 > 2s (SLO is < 500ms); DLQ depth growing | Page during business hours, investigate within 30 min |
| SEV3 | A non-critical path is degraded, or a single-user issue | AI assistant returning insufficient-context more than expected; one borrower's fast-lookup stale | Ticket, investigate within a business day |

## Escalation path

This capstone has a single-person team (`docs/requirements/team-charter.md`) — there is no
second-line/manager escalation chain to document here beyond "the on-call person is the whole
team." What's documented instead is the **order of investigation**, which matters regardless of
team size:

1. **Check `/actuator/health` (Java services) or `/health` (Python services) first** — rules out
   "the process is just down" before debugging application logic.
2. **Pull logs by correlation ID** if a specific request is implicated:
   `index=mortgage_dev correlationId="<id>"` (Splunk — see [slo.md](./slo.md) for ingestion
   status) or `docker compose logs <service> | grep <correlationId>` locally.
3. **Check the messaging runbook** ([messaging-runbook.md](./messaging-runbook.md)) if the
   symptom involves events not being consumed — DLQ depth, `event_inbox` not growing.
4. **Check the data pipeline runbook** ([data-pipeline-runbook.md](./data-pipeline-runbook.md))
   if the symptom is a reconciliation failure or stale curated data.
5. **Write the RCA** ([rca-template.md](./rca-template.md)) once the incident is understood,
   regardless of how small — a SEV3 with no RCA is a SEV1 the next time the same root cause
   recurs undiagnosed.

## Communication

No external status page or customer communication channel exists for this capstone (synthetic
data, no real users). In a real deployment, this section would name the status page, the
customer-facing communication owner, and the internal channel (Slack/Teams) incidents are
declared in.

## After the incident

Every RCA's corrective/preventive actions get tracked the same way as the M6 remediation
backlog — an owner and a status, not just a paragraph that's never revisited. See
[rca-template.md](./rca-template.md) for the required sections.
