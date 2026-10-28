# Terraform (M9)

```text
terraform/
├── modules/
│   ├── networking/   VPC, subnets, security groups (app/data tier split)
│   ├── security/     IAM roles wrapping infrastructure/aws/iam/ policy JSON (M8)
│   ├── storage/      S3 buckets + DynamoDB tables (M5/M8)
│   ├── messaging/    SNS topic, SQS queues + DLQ, subscriptions (M5)
│   └── compute/      ECS Fargate placeholder — see "Why compute is disabled" below
└── environments/
    ├── dev/     local state, targets LocalStack — the only one actually applied
    ├── test/    real AWS, S3+DynamoDB remote backend — never applied (no AWS account)
    └── prod/    same as test, plus a CI manual-approval gate (docs/operations/cicd.md)
```

## Why `dev` uses local state and targets LocalStack

This build environment has no real AWS account (same reasoning as M5/M8 — see
`docs/operations/messaging-runbook.md`). `dev/providers.tf` points the AWS provider at
LocalStack (`http://localhost:4566`) via `use_localstack = true` (the default) and uses
Terraform's local state backend so `terraform init` doesn't need a real S3 bucket to exist
first. Flip `use_localstack = false` and this same configuration targets real AWS.

**Actually run and verified, not just planned:**

```bash
cd infrastructure/terraform/environments/dev
terraform init
terraform plan -out=tfplan.out
terraform apply tfplan.out
# Apply complete! Resources: 30 added, 0 changed, 0 destroyed.
```

## Why `test`/`prod` have never been applied

Their `providers.tf` declares the exact S3+DynamoDB remote backend from the milestone spec:

```hcl
terraform {
  backend "s3" {
    bucket         = "capstone-mortgage-tfstate-test"   # tfstate-prod for prod
    key            = "mortgage-intelligence/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "capstone-mortgage-tflock-test"     # state locking
    encrypt        = true
  }
}
```

`terraform init` for either of these would try to read/create that real S3 bucket and DynamoDB
lock table, which don't exist (no AWS account). They're validated with
`terraform init -backend=false && terraform validate` instead — confirms the HCL is syntactically
correct and every module reference resolves, without needing real AWS credentials.

## Why `compute` is disabled for `dev`

Running `terraform apply` against LocalStack Community with the compute module enabled fails:

```text
Error: creating ECS Cluster (capstone-mortgage-dev): ... api error InternalFailure:
API for service 'ecs' not yet implemented or pro feature
```

ECS cluster/task-definition creation is a **LocalStack Pro** feature — confirmed by actually
running it, not assumed. `dev/main.tf` wraps the compute module in `count = var.enable_compute ?
1 : 0`, defaulting to `false`. Set `-var enable_compute=true` against real AWS or LocalStack Pro.
The module itself (`modules/compute/main.tf`) is complete, real Terraform — it's the Fargate
task definitions for `mortgage-service` and `servicing-service`, documented there as a
placeholder since this capstone actually runs containers via `docker-compose.yml`, not ECS.

## Drift detection (task 9.2 mini exercise) — actually demonstrated

```bash
# 1. Manually change what Terraform manages
aws --endpoint-url=http://localhost:4566 s3api put-bucket-encryption \
  --bucket capstone-mortgage-docs-dev \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"}}]}'

# 2. Plan shows the diff
terraform plan
#   ~ resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
#       - sse_algorithm = "aws:kms" -> null
#       + sse_algorithm = "AES256"

# 3. Remediate via code, not by hand
terraform apply -auto-approve
# Apply complete! Resources: 0 added, 1 changed, 0 destroyed.
```

## Module variables

Every module takes `environment` (dev/test/prod) and names its own resources
`capstone-mortgage-{resource}-${environment}`, matching
`guides/standards.md`'s AWS resource naming convention. `security` additionally takes `iam_dir`
pointing at `infrastructure/aws/iam/` so the policy JSON stays the single source of truth instead
of being re-typed into HCL.

## Separate roles for Terraform vs. the application (M9 implementation requirement)

Terraform itself runs with whatever credentials/role the CI pipeline or operator provides —
**never** one of the three application roles in `docs/architecture/aws-iam-matrix.md`
(`mortgage-analytics-role`, `mortgage-api-role`, `lambda-doc-processor-role`). Those three are
what the *running services* assume; Terraform needs broader provisioning permissions
(`iam:CreateRole`, `s3:CreateBucket`, etc.) that none of the application roles have or should
have. No CI identity/role has been provisioned in this build (no real AWS account), so this is
documented policy, not yet wired into a pipeline — tracked the same way as the rest of this
milestone's AWS-account-dependent pieces.
