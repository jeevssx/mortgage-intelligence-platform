# ADR-003: Servicing updates stay on SNS/SQS — no Kinesis stream added in M8

## Status

Accepted — Milestone 8 (Week 10). The spec explicitly allows this: "Enhance event flow with
Kinesis stream **or** justify SQS-only in ADR if account limits apply"
([m08-aws-data-platform.md](https://github.com/UID-Technologies/capstone-secondary-mortgage-intelligence-platform/blob/main/milestones/m08-aws-data-platform.md) task 8.4).

## Context

M5 already built an SNS → SQS → DLQ lifecycle event backbone (`capstone-mortgage-lifecycle-dev`
→ `capstone-mortgage-servicing-dev`) that `servicing-service` consumes to write through to
DynamoDB (M8 task 8.4, [ADR-002](./ADR-002-microservice-decomposition.md)). M8's task list adds
"Kinesis stream for servicing updates" as a second option alongside the existing SQS consumer.

## Decision

**No Kinesis stream was added.** The existing SQS consumer already carries every servicing
update (`MortgageCreated`, `LoanApproved`, `PaymentReceived`, `PaymentMissed`, `LoanDelinquent`)
at the volume this capstone actually produces (dozens of events per demo session). Kinesis earns
its complexity — shard management, a consumer library with checkpointing (KCL or a hand-rolled
equivalent), per-shard throughput limits — at a throughput and fan-out scale this platform
doesn't have: a single ordered, replayable high-throughput stream feeding multiple independent
consumer applications (e.g. a real-time dashboard, a fraud-detection pipeline, and the existing
DynamoDB write-through, all reading the same stream independently with their own checkpoints).
Right now there is exactly one consumer (`servicing-service`'s DynamoDB write-through), which is
precisely the shape SQS is designed for, not Kinesis.

Adding a Kinesis stream that duplicates the same five event types with no second consumer would
be complexity without a corresponding capability gain — the same anti-pattern this capstone's
own `security-controls.md` and `ADR-002` argue against elsewhere (don't add infrastructure a
system doesn't need yet).

## When to revisit

Add a Kinesis stream (`capstone-mortgage-servicing-updates-dev`, per the naming convention in
`guides/standards.md`) when a **second independent consumer** needs the same event stream with
its own replay/checkpoint position — for example, a future real-time analytics dashboard that
needs to re-read the last hour of events independently of whatever `servicing-service` has
already consumed and deleted from SQS. SQS messages are gone after one consumer deletes them;
Kinesis retains records for all consumers for the stream's retention window (24 hours to 365
days) regardless of what any one consumer has processed. That replay-for-multiple-independent-
readers capability is the actual reason to reach for Kinesis over SQS — not "more throughput"
alone, which SQS also scales to handle for this platform's realistic volume.

## Consequences

- `servicing-service`'s DynamoDB write-through (M8 task 8.4) continues to run off the existing
  SQS consumer (`SqsEventConsumer`, M5) — no new infrastructure, no new consumer code path.
- If a second consumer need arises later, introducing Kinesis means the **producer side**
  (`mortgage-service`'s `SnsEventPublisher`) needs a second publish target (SNS can fan out to
  both an SQS queue and a Kinesis stream via separate subscriptions, so this is additive, not a
  rewrite) — tracked as a future enhancement, not built here.
