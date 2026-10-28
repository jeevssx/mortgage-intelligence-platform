# Data pipeline runbook (M8)

Pipeline: `PostgreSQL -> export/S3 raw -> transform (Glue-equivalent) -> S3 curated -> reconciliation`.
Scripts: [infrastructure/data-pipeline/scripts/](../../infrastructure/data-pipeline/scripts/).
Schema: [infrastructure/data-pipeline/schemas/delinquency_report.schema.json](../../infrastructure/data-pipeline/schemas/delinquency_report.schema.json).
IAM: [aws-iam-matrix.md](../architecture/aws-iam-matrix.md) (`mortgage-analytics-role`).

## Why a pandas script instead of a real AWS Glue job

AWS Glue job *execution* requires either a real AWS account or LocalStack **Pro** — Community
edition only stubs a few Glue Data Catalog APIs, it cannot actually run a Glue job. Neither a
real account nor a Pro subscription is available in this build environment (see
[messaging-runbook.md](./messaging-runbook.md) for the same cost-avoidance reasoning applied to
SNS/SQS in M5). `transform_to_curated.py` does exactly what a Glue PySpark job would do — read
raw, join, validate schema, write curated Parquet — as a plain pandas script runnable anywhere
with `pip install -r requirements.txt`. Porting it to a real Glue job later is a packaging
change (wrap the same read/join/validate/write steps in a Glue script shell and a `glueContext`),
not a rewrite.

## Schedule and owner

Not scheduled yet (no CI/CD cron or EventBridge rule in this build — that lands in M9's
Terraform/CI work). Today it's a **manual three-step run**:

```bash
# 1. Export (needs PGHOST/PGUSER/PGPASSWORD/PGDATABASE for the mortgage_app role)
DATE=2026-03-15 bash infrastructure/data-pipeline/scripts/export_to_raw.sh

# 2. Transform (needs AWS_ENDPOINT_URL for LocalStack, or unset for real AWS)
cd infrastructure/data-pipeline
pip install -r requirements.txt
python3 scripts/transform_to_curated.py --date 2026-03-15

# 3. Reconcile (fails with exit code 1 if either tolerance is exceeded)
PGHOST=localhost PGUSER=mortgage_app PGPASSWORD=... PGDATABASE=mortgage_intel \
  python3 scripts/reconcile.py --date 2026-03-15
```

**Owner:** platform maintainer (sole team member on this capstone — see
[team-charter.md](../requirements/team-charter.md)). A real deployment should run this on a
schedule (EventBridge → Lambda, or a Glue trigger) and alert the on-call owner on reconciliation
failure — tracked as a follow-up, not built here.

## Reconciliation tolerances

| Check | Tolerance | Rationale |
| --- | --- | --- |
| Row count, PG `mortgage` vs curated `delinquency_report` | 0 | Every mortgage must appear exactly once; any difference means rows were dropped or duplicated in the join |
| `SUM(outstanding_balance)` | ± 0.01 | Floating-point rounding only; anything larger means a join or currency-handling bug |

Verified live against the real seed data: `reconcile.py` reported `PG=13 curated=13 diff=0` and
matching balance sums, exit code 0, after a real `export_to_raw.sh` → `transform_to_curated.py`
run (not just the mocked unit tests in `infrastructure/data-pipeline/tests/`).

## Schema drift

**What's handled automatically** (`transform_to_curated.py`, tested in
`infrastructure/data-pipeline/tests/test_transform.py`):

| Scenario | Behavior |
| --- | --- |
| A new column appears in the raw export (e.g. someone adds `loan_officer_notes` to the PG export query) | Logged as a `WARNING` ("unexpected extra column"), dropped from curated output, pipeline continues. This is additive schema evolution — nothing downstream was relying on a column that didn't exist before. |
| A required column disappears (e.g. a migration renames `outstanding_balance`) | Raises `SchemaDriftError`, logged as `SCHEMA_DRIFT_ALERT`, **exit code 1** — the pipeline stops rather than writing a curated file with missing/garbage data. |

**If you hit a `SCHEMA_DRIFT_ALERT` in practice:**

1. Check what changed: `git log -p -- database/migrations/` for a recent column rename/drop on
   `mortgage` or `delinquency`.
2. If the column was intentionally renamed, update `EXPECTED_MORTGAGE_COLUMNS` /
   `EXPECTED_DELINQUENCY_COLUMNS` in `transform_to_curated.py` and
   `infrastructure/data-pipeline/schemas/delinquency_report.schema.json` to match, bump the
   schema's `version` field, and re-run.
3. If the column disappeared unintentionally (e.g. a bad migration), fix the migration instead
   of the pipeline — do not silently adapt the schema to a mistake.
4. Re-run all three pipeline steps for the affected date before trusting any report built from
   that date's curated data.

## Validating a fresh pipeline run

```bash
cd infrastructure/data-pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -v   # 4 tests: happy path, additive drift, missing-column drift, parquet round-trip
```
