# ADR-002: Microservice decomposition and event backbone

## Status

Accepted — Milestone 5 (Week 6).

## Context

Through M4 the platform is "multiple services in one repo" sharing a database with no
asynchronous communication. M5 asks for documented service boundaries, an event backbone
(SNS → SQS → consumer, with a DLQ), and containerized services
([m05-microservices-events-containers.md](../../milestones/m05-microservices-events-containers.md)).

We do not have a real AWS account provisioned for this capstone build (cost/approval overhead
outweighs the benefit at this stage — see [reference.aws-local-only](../../docs/operations/messaging-runbook.md)).
LocalStack gives the same SNS/SQS/DLQ semantics against `localhost:4566` with zero cloud cost and
no credentials to manage, so all AWS SDK usage targets it via `AWS_ENDPOINT_URL`. The same code
runs unmodified against real AWS by unsetting that variable, per `guides/standards.md` resource
naming (`capstone-mortgage-{resource}-{env}`).

## Decision

**Service boundaries** (see [service-ownership-matrix.md](../architecture/service-ownership-matrix.md)
for the full table):

- `mortgage-service` owns borrower/mortgage/loan/payment writes and is the sole **producer** of
  lifecycle events: `MortgageCreated`, `LoanApproved`, `PaymentReceived`, `PaymentMissed`.
- `servicing-service` owns servicing-history/delinquency reads, keeps its ADR-001 DB-read
  ownership, and is the **consumer** of `capstone-mortgage-servicing-dev` plus the producer of
  `LoanDelinquent` (via its existing internal `POST .../servicing-events` endpoint).
- `mortgage-analytics-service` is an optional, not-yet-wired consumer of
  `capstone-mortgage-analytics-dev` (cache-refresh use case) — reserved for a later milestone.

**Event backbone:** one SNS topic (`capstone-mortgage-lifecycle-dev`) fans out to per-consumer SQS
queues, each with a dead-letter queue after 3 failed receives (`guides/standards.md` naming):

```text
mortgage-service --publish--> SNS capstone-mortgage-lifecycle-dev
                                 |--> SQS capstone-mortgage-servicing-dev --> servicing-service
                                 |       (DLQ: capstone-mortgage-servicing-dlq-dev)
                                 '--> SQS capstone-mortgage-analytics-dev --> (reserved, no consumer yet)
```

**Why events don't replace the M4 direct writes.** `mortgage-service` already writes
`servicing_history` rows synchronously inside the payment transaction (M4, ADR-001) — that stays
the system of record so M4's tests and demo script keep working unmodified. The SQS consumer in
`servicing-service` does **not** duplicate those rows; it records each event's `eventId` into a
new `event_inbox` table (idempotent dedupe) and logs it. This demonstrates the async lifecycle
and DLQ mechanics — the actual M5 teaching goal — without creating two conflicting writers to the
same table. A future milestone can move the write itself behind the queue if the team decides to
split the database per service.

**Schema versioning:** every event envelope carries `schemaVersion` (starts at `1`). Breaking
changes (removed/retyped fields) require a new major version and a new SNS topic or a
`schemaVersion` branch in the consumer — never an in-place incompatible change to an existing
version.

## Consequences

- Event publish failures are logged at `ERROR` and swallowed — they must never roll back the
  HTTP transaction that triggered them. Lifecycle events are at-least-once and best-effort;
  consumers must be idempotent (`event_inbox`), and a dropped publish is a monitoring gap, not a
  data-loss bug, because the database write already happened.
- `servicing-service` gets a new outbound dependency (SQS polling) and a new write path
  (`event_inbox`) in addition to its M4 read-only role.
- No cyclic dependency is introduced: `mortgage-service` never calls `servicing-service` or vice
  versa; all cross-service communication is one-way through SNS/SQS.
