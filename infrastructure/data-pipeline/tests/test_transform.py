"""M8 task 8.6 — schema drift test, plus the normal happy path.

Run: pip install -r ../requirements.txt -r requirements-dev.txt && pytest -v
"""

import io
import sys
from pathlib import Path

import boto3
import pandas as pd
import pytest
from moto import mock_aws

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import transform_to_curated as t  # noqa: E402

BUCKET = "capstone-mortgage-analytics-dev"
DATE = "2026-03-15"


def _put_csv(s3, key: str, df: pd.DataFrame) -> None:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    s3.put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue().encode())


def _seed_raw(s3, *, extra_mortgage_column: bool = False, drop_column: str | None = None) -> None:
    mortgage_df = pd.DataFrame(
        {
            "mortgage_id": ["m-1", "m-2"],
            "mortgage_external_id": ["MTG-1001", "MTG-1002"],
            "status": ["ACTIVE", "DELINQUENT"],
            "original_amount": [310000.0, 320000.0],
            "outstanding_balance": [305000.0, 308500.0],
            "origination_date": ["2024-01-15", "2024-02-01"],
        }
    )
    if extra_mortgage_column:
        mortgage_df["loan_officer_notes"] = ["n/a", "n/a"]  # additive drift
    if drop_column:
        mortgage_df = mortgage_df.drop(columns=[drop_column])

    delinquency_df = pd.DataFrame(
        {
            "mortgage_id": ["m-2"],
            "delinquent_since": ["2026-01-10"],
            "days_past_due": [45],
            "severity": ["MODERATE"],
        }
    )

    _put_csv(s3, f"raw/pg-export/date={DATE}/mortgage.csv", mortgage_df)
    _put_csv(s3, f"raw/pg-export/date={DATE}/delinquency.csv", delinquency_df)


@pytest.fixture
def s3():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield client


def test_transform_joins_mortgage_and_delinquency(s3):
    _seed_raw(s3)

    df = t.transform(BUCKET, DATE)

    assert len(df) == 2
    row = df[df["mortgage_external_id"] == "MTG-1002"].iloc[0]
    assert row["status"] == "DELINQUENT"
    assert row["days_past_due"] == 45
    assert row["as_of_date"] == DATE
    # MTG-1001 was never delinquent — left join leaves these null, not zero/fabricated.
    active_row = df[df["mortgage_external_id"] == "MTG-1001"].iloc[0]
    assert pd.isna(active_row["days_past_due"])


def test_additive_schema_drift_is_logged_and_tolerated(s3, caplog):
    """M8 task 8.6: a new column in the raw export (e.g. ops added `loan_officer_notes` to the
    PG export query) must not break the pipeline — it's dropped from curated output with a
    warning, not silently included or fatally rejected."""
    _seed_raw(s3, extra_mortgage_column=True)

    df = t.transform(BUCKET, DATE)

    assert len(df) == 2
    assert "loan_officer_notes" not in df.columns
    assert any("unexpected extra column" in record.message for record in caplog.records)


def test_missing_required_column_raises_schema_drift_error(s3):
    """M8 task 8.6: a REQUIRED column disappearing (e.g. a PG migration renamed
    outstanding_balance) must fail loudly, not produce a curated file with missing/garbage data."""
    _seed_raw(s3, drop_column="outstanding_balance")

    with pytest.raises(t.SchemaDriftError, match="outstanding_balance"):
        t.transform(BUCKET, DATE)


def test_write_curated_round_trips_through_parquet(s3):
    _seed_raw(s3)
    df = t.transform(BUCKET, DATE)

    key = t.write_curated(df, BUCKET, DATE)

    body = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
    read_back = pd.read_parquet(io.BytesIO(body))
    assert len(read_back) == len(df)
    assert key == f"curated/delinquency_report/date={DATE}/part-0000.parquet"
