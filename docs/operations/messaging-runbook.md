# Messaging runbook (M5)

Event catalog: [docs/architecture/event-catalog.md](../architecture/event-catalog.md). Topology
and ADR: [ADR-002](../adr/ADR-002-microservice-decomposition.md).

## Why LocalStack, not real AWS, for this build

No AWS account is provisioned for the capstone build. Creating one is free, but NAT
gateways/RDS/Glue left running by accident bill hourly regardless of use — easy to forget and
rack up real charges on a learner project. [LocalStack](https://docs.localstack.cloud/) at
`localhost:4566` gives the same SNS/SQS/DLQ API surface with zero cost and no credentials. The
AWS SDK code is identical either way — point `AWS_ENDPOINT_URL` at LocalStack for local/CI runs,
or unset it entirely to hit real AWS with an `AWS_PROFILE` / IAM role.

## Resources (dev)

| Resource | Name | Notes |
| --- | --- | --- |
| SNS topic | `capstone-mortgage-lifecycle-dev` | one topic, all five lifecycle events |
| SQS queue | `capstone-mortgage-servicing-dev` | consumed by `servicing-service` |
| SQS DLQ | `capstone-mortgage-servicing-dlq-dev` | redrive after 3 failed receives |
| SQS queue | `capstone-mortgage-analytics-dev` | reserved, no consumer wired yet |

Created by [infrastructure/localstack/bootstrap.sh](../../infrastructure/localstack/bootstrap.sh),
which runs automatically as the `localstack-init` service in `docker-compose.yml`.

## SQS settings

- Visibility timeout: 30s
- `maxReceiveCount`: 3 before a message moves to the DLQ
- `RawMessageDelivery`: `true` on both SNS→SQS subscriptions (consumers read the event envelope
  directly, not an SNS-wrapped string)

## Operating the stack locally

```bash
docker compose up --build -d
docker compose ps                      # all services "healthy"

# Inspect queues
aws --endpoint-url=http://localhost:4566 sqs list-queues
aws --endpoint-url=http://localhost:4566 sqs get-queue-attributes \
  --queue-url http://localhost:4566/000000000000/capstone-mortgage-servicing-dev \
  --attribute-names ApproximateNumberOfMessages
```

## Demo: publish and consume

```bash
curl -s -X POST http://localhost:8080/api/v1/mortgages -H "Content-Type: application/json" -d '{
  "mortgageExternalId": "MTG-1020", "borrowerExternalId": "BOR-001",
  "originalAmount": 250000.00, "outstandingBalance": 250000.00,
  "originationDate": "2026-01-01",
  "loan": {"loanExternalId": "LOAN-2020", "interestRate": 0.0599, "termMonths": 360, "underwritingDecision": "APPROVED"}
}'
# -> publishes MortgageCreated and LoanApproved to the SNS topic

docker compose logs servicing-service --tail=20
# -> "Processed event eventType=MortgageCreated eventId=... mortgageExternalId=MTG-1020"
# -> "Processed event eventType=LoanApproved eventId=... mortgageExternalId=MTG-1020"
```

## Demo: force a DLQ delivery

The consumer throws (without acking) for a synthetic event type reserved for this drill:

```bash
aws --endpoint-url=http://localhost:4566 sns publish \
  --topic-arn arn:aws:sns:us-east-1:000000000000:capstone-mortgage-lifecycle-dev \
  --message '{"eventId":"11111111-1111-1111-1111-111111111111","eventType":"FORCE_FAILURE_TEST","occurredAt":"2026-01-01T00:00:00Z","schemaVersion":1,"correlationId":"dlq-drill","payload":{}}' \
  --message-attributes '{"eventType":{"DataType":"String","StringValue":"FORCE_FAILURE_TEST"}}'

# Wait ~2 minutes (3 receives x 30s visibility timeout), then:
aws --endpoint-url=http://localhost:4566 sqs get-queue-attributes \
  --queue-url http://localhost:4566/000000000000/capstone-mortgage-servicing-dlq-dev \
  --attribute-names ApproximateNumberOfMessages
# -> ApproximateNumberOfMessages: "1"
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `servicing-service` logs `UNEXPECTED_ERROR` on every poll | `AWS_ENDPOINT_URL` not set to `http://localstack:4566` inside the container network | Check `docker-compose.yml` environment block |
| Queue depth grows but nothing in logs | `localstack-init` didn't run (queue doesn't exist yet) | `docker compose logs localstack-init`; re-run `bootstrap.sh` manually |
| Duplicate `event_inbox` rows | Should never happen — dedupe is a `PRIMARY KEY` on `event_id` | Check for a second consumer process running against the same queue |
| `MortgageCreated` never appears | SNS publish failures are logged at `ERROR` and swallowed (ADR-002) so the HTTP call still succeeds | Check `mortgage-service` logs for `EVENT_PUBLISH_FAILED` |
