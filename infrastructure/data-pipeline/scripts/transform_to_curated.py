#!/usr/bin/env python3
"""M8 task 8.5 step 2 — the "Glue job" for this capstone.

Reads raw/pg-export/date=.../{mortgage,delinquency}.csv from S3, joins them, and writes
curated/delinquency_report/date=.../part-0000.parquet, validated against
infrastructure/data-pipeline/schemas/delinquency_report.schema.json.

Written as a plain pandas script rather than an actual AWS Glue job: Glue job *execution*
requires LocalStack Pro or a real AWS account, neither available in this build environment (see
docs/operations/data-pipeline-runbook.md). The transformation logic itself is what a Glue
PySpark job would do — read raw, join, validate schema, write curated Parquet — so porting this
to a real Glue job later is a packaging change, not a rewrite.

Usage:
  AWS_ENDPOINT_URL=http://localhost:4566 python3 transform_to_curated.py --date 2026-03-15
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import sys
from pathlib import Path

import boto3
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("transform_to_curated")

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "delinquency_report.schema.json"
EXPECTED_MORTGAGE_COLUMNS = {
    "mortgage_id", "mortgage_external_id", "status", "original_amount", "outstanding_balance", "origination_date",
}
EXPECTED_DELINQUENCY_COLUMNS = {"mortgage_id", "delinquent_since", "days_past_due", "severity"}


class SchemaDriftError(RuntimeError):
    """A required column is missing from the raw export — this must stop the pipeline, not
    silently produce a curated file with missing data (M8 task 8.6)."""


def _s3_client():
    return boto3.client("s3", endpoint_url=os.environ.get("AWS_ENDPOINT_URL") or None)


def _read_csv_from_s3(s3, bucket: str, key: str) -> pd.DataFrame:
    body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    return pd.read_csv(io.BytesIO(body))


def _check_schema(df: pd.DataFrame, expected: set[str], label: str) -> None:
    actual = set(df.columns)
    missing = expected - actual
    extra = actual - expected
    if missing:
        raise SchemaDriftError(f"{label}: missing required column(s) {sorted(missing)} — refusing to run")
    if extra:
        # Additive drift: a new column appeared. Log and proceed (schema evolution), rather than
        # failing, since dropping a column we didn't expect loses nothing we were relying on.
        logger.warning("%s: unexpected extra column(s) %s — ignored, not written to curated output", label, sorted(extra))


def transform(bucket: str, date: str) -> pd.DataFrame:
    s3 = _s3_client()
    raw_prefix = f"raw/pg-export/date={date}"

    mortgage_df = _read_csv_from_s3(s3, bucket, f"{raw_prefix}/mortgage.csv")
    _check_schema(mortgage_df, EXPECTED_MORTGAGE_COLUMNS, "mortgage.csv")

    delinquency_df = _read_csv_from_s3(s3, bucket, f"{raw_prefix}/delinquency.csv")
    _check_schema(delinquency_df, EXPECTED_DELINQUENCY_COLUMNS, "delinquency.csv")

    merged = mortgage_df.merge(delinquency_df, on="mortgage_id", how="left")
    merged["as_of_date"] = date

    curated_columns = [c["name"] for c in json.loads(SCHEMA_PATH.read_text())["columns"]]
    return merged[curated_columns]


def write_curated(df: pd.DataFrame, bucket: str, date: str) -> str:
    s3 = _s3_client()
    key = f"curated/delinquency_report/date={date}/part-0000.parquet"
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False)
    s3.put_object(Bucket=bucket, Key=key, Body=buffer.getvalue())
    return key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="Partition date, e.g. 2026-03-15")
    parser.add_argument("--bucket", default=os.environ.get("ANALYTICS_BUCKET", "capstone-mortgage-analytics-dev"))
    args = parser.parse_args()

    try:
        df = transform(args.bucket, args.date)
    except SchemaDriftError as exc:
        logger.error("SCHEMA_DRIFT_ALERT: %s", exc)
        sys.exit(1)

    key = write_curated(df, args.bucket, args.date)
    logger.info("Wrote %d rows to s3://%s/%s", len(df), args.bucket, key)


if __name__ == "__main__":
    main()
