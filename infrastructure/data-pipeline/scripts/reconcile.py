#!/usr/bin/env python3
"""M8 task 8.6 — reconciliation: compare PostgreSQL against the curated Parquet file.

Tolerances (docs/operations/data-pipeline-runbook.md):
  row count PG vs curated      : 0 difference
  sum(outstanding_balance)     : +/- 0.01

Usage:
  PGHOST=localhost PGUSER=mortgage_app PGPASSWORD=... PGDATABASE=mortgage_intel \
    AWS_ENDPOINT_URL=http://localhost:4566 \
    python3 reconcile.py --date 2026-03-15
Exit code 0 = PASS, 1 = FAIL (so this can gate a scheduled pipeline run).
"""

from __future__ import annotations

import argparse
import io
import logging
import os
import sys

import boto3
import pandas as pd
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("reconcile")

ROW_COUNT_TOLERANCE = 0
BALANCE_SUM_TOLERANCE = 0.01


def _pg_counts() -> tuple[int, float]:
    conn = psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "mortgage_intel"),
        user=os.environ.get("PGUSER", "mortgage_app"),
        password=os.environ.get("PGPASSWORD", ""),
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), SUM(outstanding_balance) FROM mortgage")
            row_count, balance_sum = cur.fetchone()
            return row_count, float(balance_sum)
    finally:
        conn.close()


def _curated_counts(bucket: str, date: str) -> tuple[int, float]:
    s3 = boto3.client("s3", endpoint_url=os.environ.get("AWS_ENDPOINT_URL") or None)
    key = f"curated/delinquency_report/date={date}/part-0000.parquet"
    body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    df = pd.read_parquet(io.BytesIO(body))
    return len(df), float(df["outstanding_balance"].sum())


def reconcile(bucket: str, date: str) -> bool:
    pg_rows, pg_balance = _pg_counts()
    curated_rows, curated_balance = _curated_counts(bucket, date)

    row_diff = abs(pg_rows - curated_rows)
    balance_diff = abs(pg_balance - curated_balance)

    row_pass = row_diff <= ROW_COUNT_TOLERANCE
    balance_pass = balance_diff <= BALANCE_SUM_TOLERANCE

    logger.info("Row count:   PG=%d  curated=%d  diff=%d  tolerance=%d  %s",
                pg_rows, curated_rows, row_diff, ROW_COUNT_TOLERANCE, "PASS" if row_pass else "FAIL")
    logger.info("Balance sum: PG=%.2f  curated=%.2f  diff=%.4f  tolerance=%.2f  %s",
                pg_balance, curated_balance, balance_diff, BALANCE_SUM_TOLERANCE, "PASS" if balance_pass else "FAIL")

    return row_pass and balance_pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--bucket", default=os.environ.get("ANALYTICS_BUCKET", "capstone-mortgage-analytics-dev"))
    args = parser.parse_args()

    ok = reconcile(args.bucket, args.date)
    logger.info("RECONCILIATION %s", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
