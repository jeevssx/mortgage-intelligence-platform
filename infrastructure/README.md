# Infrastructure

```text
infrastructure/
├── aws/
│   ├── iam/              least-privilege policy JSON + the M8 over-permissioned mini exercise
│   └── lambda/
│       └── doc-processor/   S3-triggered document metadata Lambda (M8 task 8.3)
├── data-pipeline/
│   ├── scripts/          PostgreSQL -> S3 raw -> curated transform -> reconciliation (M8 task 8.5-8.6)
│   └── schemas/          expected curated-zone column schema
├── localstack/           bootstrap.sh — SNS/SQS/S3/DynamoDB setup for local dev (M5, M8)
└── terraform/            modules + dev/test/prod environments (M9) — see terraform/README.md
```

Everything under `aws/` and `data-pipeline/` targets [LocalStack](https://localstack.cloud/) by
default (`AWS_ENDPOINT_URL=http://localhost:4566` or the docker-compose `localstack` service) —
no AWS account needed for local dev or CI. See
[docs/architecture/aws-iam-matrix.md](../docs/architecture/aws-iam-matrix.md) and
[docs/operations/data-pipeline-runbook.md](../docs/operations/data-pipeline-runbook.md) for the
full picture, and [ADR-003](../docs/adr/ADR-003-kinesis-vs-sqs-only.md) for why there's no
Kinesis stream here.
