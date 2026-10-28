#!/usr/bin/env bash
# M8 task 8.5 step 1: export mortgage + delinquency tables from PostgreSQL to the S3 raw zone.
# Run from database/ or anywhere with PGHOST/PGUSER/PGPASSWORD/PGDATABASE set for mortgage_app.
#
# Usage: DATE=2026-03-15 bash infrastructure/data-pipeline/scripts/export_to_raw.sh
set -euo pipefail

DATE="${DATE:-$(date +%Y-%m-%d)}"
BUCKET="${ANALYTICS_BUCKET:-capstone-mortgage-analytics-dev}"
ENDPOINT_FLAG=""
if [ -n "${AWS_ENDPOINT_URL:-}" ]; then
  ENDPOINT_FLAG="--endpoint-url=${AWS_ENDPOINT_URL}"
fi

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "Exporting mortgage and delinquency tables for date=$DATE ..."
# mortgage.csv keeps the internal `id` (aliased mortgage_id) so transform_to_curated.py can join
# it against delinquency.csv's mortgage_id FK — the raw zone stays source-table-shaped; the join
# happens in the transform step, same as a real Glue job would do it.
psql -v ON_ERROR_STOP=1 -c "\copy (SELECT id AS mortgage_id, mortgage_external_id, status, original_amount, outstanding_balance, origination_date FROM mortgage) TO '$WORKDIR/mortgage.csv' CSV HEADER"
psql -v ON_ERROR_STOP=1 -c "\copy (SELECT mortgage_id, delinquent_since, days_past_due, severity FROM delinquency) TO '$WORKDIR/delinquency.csv' CSV HEADER"

PREFIX="raw/pg-export/date=$DATE"
echo "Uploading to s3://$BUCKET/$PREFIX/"
aws $ENDPOINT_FLAG s3 cp "$WORKDIR/mortgage.csv" "s3://$BUCKET/$PREFIX/mortgage.csv"
aws $ENDPOINT_FLAG s3 cp "$WORKDIR/delinquency.csv" "s3://$BUCKET/$PREFIX/delinquency.csv"

echo "Done. Raw export at s3://$BUCKET/$PREFIX/"
echo "RAW_PREFIX=$PREFIX" # consumed by transform_to_curated.py when chained in a script
