# ADR-001: Service data ownership between mortgage-service and servicing-service

## Status

Accepted — Milestone 4 (Weeks 4-5).

## Context

M4 introduces two Java/Spring Boot services on the M2 PostgreSQL schema: `mortgage-service`
(port 8080) and `servicing-service` (port 8081). Both need `mortgage`, `servicing_history`, and
`delinquency` data. The spec ([m04-java-spring-backend.md](../../milestones/m04-java-spring-backend.md)
in the capstone handbook) allows either a shared database or an API-only split, documented here.

## Decision

Both services connect directly to the same `mortgage_intel` database as the `mortgage_app` role
(shared database, no inter-service HTTP calls for this milestone):

- **mortgage-service** owns writes: `borrower`, `mortgage`, `loan`, `payment`, and the
  `servicing_history` rows it generates as a side effect of onboarding and payment posting
  (`ONBOARDING_COMPLETE`, `PAYMENT_POSTED` / `PAYMENT_FAILED` / `PAYMENT_REVERSED` /
  `PAYMENT_SCHEDULED`).
- **servicing-service** owns reads of `mortgage` (status only), `servicing_history`, and
  `delinquency`. It also exposes one write path, `POST /{mortgageExternalId}/servicing-events`,
  for internal/event-driven entries (e.g. document uploads, a future M5 SNS/SQS consumer) that
  don't originate from a payment.
- Neither service recomputes `delinquency` rows. Delinquency snapshots remain seed-data-driven
  (M2) until a scheduled job or event consumer (M5+) takes over; posting a payment does not flip
  `mortgage.status` to `DELINQUENT` or back.

## Consequences

- No synchronous HTTP calls between the two services yet — low latency, simple to run locally,
  but both services must agree on the schema (`guides/reference-data-model.md`) and the
  delinquency rule (`guides/standards.md`) without a shared code module.
- Each service defines its own lightweight JPA entities for tables it reads (e.g.
  `servicing-service`'s `Mortgage` entity only maps `id`, `mortgage_external_id`, `status`) to
  avoid over-fetching columns it doesn't own.
- If M5 moves to per-service databases, `servicing-service` will need an event consumer
  (`PaymentPosted` / `LoanDelinquent`) instead of direct table reads — this ADR will be
  superseded at that point.
