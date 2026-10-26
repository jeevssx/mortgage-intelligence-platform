# Event catalog (M5)

All events share an envelope (`eventId`, `eventType`, `occurredAt`, `schemaVersion`,
`correlationId`, `payload`). JSON Schemas: [docs/architecture/events/](./events/). Topology and
ADR: [service-ownership-matrix.md](./service-ownership-matrix.md),
[ADR-002](../adr/ADR-002-microservice-decomposition.md).

| Event | Producer | Consumer(s) | Schema version | Trigger |
| --- | --- | --- | --- | --- |
| `MortgageCreated` | `mortgage-service` | `servicing-service` (`event_inbox` only) | 1 | `POST /api/v1/mortgages` |
| `LoanApproved` | `mortgage-service` | `servicing-service` (`event_inbox` only) | 1 | `POST /api/v1/mortgages` with `loan.underwritingDecision=APPROVED` — stub for a real approval workflow, see Common mistakes below |
| `PaymentReceived` | `mortgage-service` | `servicing-service` (`event_inbox` only) | 1 | `POST /api/v1/mortgages/{id}/payments` with `status=POSTED` |
| `PaymentMissed` | `mortgage-service` | `servicing-service` (`event_inbox` only) | 1 | `POST /api/v1/mortgages/{id}/payments` with `status=FAILED` — stand-in for a scheduled missed-payment batch job (not built; M8+) |
| `LoanDelinquent` | `servicing-service` | *(none wired)* | 1 | `POST /api/v1/mortgages/{id}/servicing-events` with `eventType=LOAN_DELINQUENT` |

## Transport

```text
Producer --publish--> SNS capstone-mortgage-lifecycle-dev
                         |--RawMessageDelivery--> SQS capstone-mortgage-servicing-dev --> servicing-service
                         |                           (after 3 failed receives: capstone-mortgage-servicing-dlq-dev)
                         '--RawMessageDelivery--> SQS capstone-mortgage-analytics-dev (reserved, no consumer yet)
```

Local dev and CI point the AWS SDK at LocalStack (`AWS_ENDPOINT_URL=http://localhost:4566`); the
same code targets real AWS if that variable is unset. Bootstrap script:
[infrastructure/localstack/bootstrap.sh](../../infrastructure/localstack/bootstrap.sh). Runbook:
[docs/operations/messaging-runbook.md](../operations/messaging-runbook.md).

## Idempotency

`servicing-service` records every consumed `eventId` in `event_inbox`
(`database/migrations/004_event_inbox.sql`) before processing. A redelivered message with an
`eventId` already in that table is acknowledged (deleted from the queue) without reprocessing.

## Why consumers don't duplicate `servicing_history`

`mortgage-service` already writes `servicing_history` rows synchronously inside the M4 payment
transaction. The SQS consumer's job here is to prove the event pipeline and DLQ mechanics, not to
re-derive data the database already has — see the "Why events don't replace the M4 direct writes"
section of ADR-002.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| Treating `LoanApproved` as a real underwriting workflow | It fires immediately alongside `MortgageCreated` today because M4 has no separate approval step — document this as a stub, don't build downstream logic that assumes a delay |
| Assuming `PaymentMissed` runs on a schedule | It only fires on an explicit `POST .../payments` with `status=FAILED`; a real missed-payment sweep needs a batch job (M8+) |
| Forwarding the raw SNS envelope to consumers | `RawMessageDelivery=true` is set on both SQS subscriptions so consumers parse the event envelope directly, not an SNS-wrapped `Message` string |
