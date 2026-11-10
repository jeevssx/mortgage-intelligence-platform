# AWS IAM matrix (M8)

Least-privilege roles for the three AWS-touching components. Policy JSON:
[infrastructure/aws/iam/](../../infrastructure/aws/iam/). Tested against LocalStack
(`infrastructure/localstack/bootstrap.sh`) — the same JSON would apply unmodified against real
AWS, only the account ID in each ARN's `*` wildcard would become a real 12-digit ID.

## Role → service → actions

| Role | Used by | Resources | Actions |
| --- | --- | --- | --- |
| `mortgage-analytics-role` | `mortgage-analytics-service` (M3, M8) | `capstone-mortgage-docs-dev/mortgages/*`; `capstone-mortgage-analytics-dev` (+ `raw/pg-export/*`, `curated/*`); SNS topic `capstone-mortgage-lifecycle-dev` | `s3:GetObject`, `s3:PutObject`, `s3:ListBucket`, `sns:Publish` |
| `mortgage-api-role` | `mortgage-service` + `servicing-service` (M5, M8) | SNS topic `capstone-mortgage-lifecycle-dev`; SQS queue `capstone-mortgage-servicing-dev` (servicing-service only); DynamoDB table `MortgageLookup-dev` (servicing-service only) | `sns:Publish`; `sqs:ReceiveMessage`/`DeleteMessage`/`GetQueueAttributes`; `dynamodb:GetItem`/`PutItem`/`UpdateItem`/`Query` |
| `lambda-doc-processor-role` | `capstone-doc-processor-dev` Lambda (M8) | `capstone-mortgage-docs-dev/mortgages/*` (read only); DynamoDB table `DocumentMetadata-dev`; its own CloudWatch log group | `s3:GetObject`, `dynamodb:PutItem`, `logs:CreateLogGroup`/`CreateLogStream`/`PutLogEvents` |

One role is shared by both Java services (rather than two near-identical roles) because they
already share a database per [ADR-001](../adr/ADR-001-service-data-ownership.md) — splitting the
*IAM* role while the *data* ownership stays shared would just mean maintaining two policies that
drift out of sync. If a future milestone splits their databases, split this role too.

## Mini exercise: fixing an over-permissioned policy (task 8.1)

**Before** — [infrastructure/aws/iam/examples/over-permissioned-before.json](../../infrastructure/aws/iam/examples/over-permissioned-before.json),
the policy you get if you reach for `Action: "s3:*"` / `Resource: "*"` to "just make it work":

```json
{
  "Sid": "TooBroad",
  "Effect": "Allow",
  "Action": "s3:*",
  "Resource": "*"
}
```

**What's wrong:**

1. `s3:*` includes `s3:DeleteBucket`, `s3:PutBucketPolicy`, `s3:PutBucketAcl` — a compromised
   analytics service could delete the bucket or make it public, not just read/write a document.
2. `Resource: "*"` grants access to **every** bucket in the account, including ones this service
   has no business touching (buckets belonging to other teams, Terraform state buckets in M9,
   etc.) — a single over-scoped credential becomes an account-wide blast radius.
3. The same shape repeats for `dynamodb:*`/`sqs:*`/`sns:*` on `Resource: "*"` — full control over
   every table, queue, and topic, not just this service's one of each.

**After** — [infrastructure/aws/iam/mortgage-analytics-role-policy.json](../../infrastructure/aws/iam/mortgage-analytics-role-policy.json):
`s3:GetObject`/`s3:PutObject` only (no delete, no bucket admin actions), scoped to the exact
bucket ARNs and prefixes this service actually reads/writes. Same pattern applied to the other
two roles — see the table above for exactly which actions and resources each one gets, and
nothing else.

## Verifying least privilege

LocalStack Community does not enforce IAM policy restrictions at runtime (it accepts any
request regardless of attached policy), and no real AWS account was available in this build
environment to verify these policies against real IAM — so these JSON documents have been
validated by structure (valid policy syntax, correctly scoped `Resource` ARNs) and by code
review against each service's actual API calls, not by a live policy simulation. **If you have a
real AWS account**, verify before relying on this in production:

```bash
aws iam simulate-custom-policy \
  --policy-input-list file://infrastructure/aws/iam/mortgage-analytics-role-policy.json \
  --action-names s3:DeleteBucket \
  --resource-arns arn:aws:s3:::capstone-mortgage-docs-dev
# Expect: EvalDecision = implicitDeny
```
