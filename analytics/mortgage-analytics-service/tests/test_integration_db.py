"""Cross-check API results against SQL on a live PostgreSQL loaded with the M2 migrations + seed.

Skipped unless INTEGRATION_DB=1. Uses POSTGRES_* env vars (see .env.example).
    INTEGRATION_DB=1 POSTGRES_PASSWORD=... pytest -m integration -v
"""

from __future__ import annotations

import os
from datetime import date

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
from sqlalchemy import text

from src.api.main import create_app
from src.config import Settings
from src.repositories.mortgage_repository import MortgageRepository, create_db_engine

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.environ.get("INTEGRATION_DB") != "1", reason="set INTEGRATION_DB=1 to run"),
]

BUCKET = "capstone-mortgage-docs-it"


@pytest.fixture(scope="module")
def db_settings() -> Settings:
    base = Settings.from_env()
    return Settings(**{**base.__dict__, "s3_bucket_documents": BUCKET, "sns_topic_mortgage_events": None})


@pytest.fixture(scope="module")
def engine(db_settings):
    eng = create_db_engine(db_settings)
    yield eng
    eng.dispose()


@pytest.fixture(scope="module")
def client(db_settings):
    # Real repository + startup DB check; S3 is mocked.
    with mock_aws():
        os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        with TestClient(create_app(db_settings, s3_client=s3)) as test_client:
            yield test_client


def scalar(engine, sql: str, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).scalar_one()


def test_portfolio_summary_matches_sql(client, engine):
    body = client.get("/api/v1/analytics/portfolio-summary", headers={"X-Correlation-Id": "demo-m3-001"}).json()
    assert body["totalMortgages"] == scalar(engine, "SELECT COUNT(*) FROM mortgage")
    assert body["delinquentMortgages"] == scalar(engine, "SELECT COUNT(*) FROM mortgage WHERE status = 'DELINQUENT'")
    assert body["activeMortgages"] == scalar(engine, "SELECT COUNT(*) FROM mortgage WHERE status = 'ACTIVE'")
    sql_balance = scalar(
        engine, "SELECT SUM(outstanding_balance) FROM mortgage WHERE status IN ('ACTIVE','DELINQUENT')"
    )
    assert body["outstandingBalanceTotal"] == pytest.approx(float(sql_balance), abs=0.005)
    sql_rate = scalar(
        engine,
        """SELECT ROUND(COUNT(*) FILTER (WHERE status='DELINQUENT')::numeric
                 / NULLIF(COUNT(*) FILTER (WHERE status IN ('ACTIVE','DELINQUENT')), 0), 4) FROM mortgage""",
    )
    assert body["delinquencyRate"] == pytest.approx(float(sql_rate))
    assert body["delinquentMortgages"] >= 1


def test_seed_expectations(client):
    body = client.get("/api/v1/analytics/portfolio-summary").json()
    assert body["totalMortgages"] == 12
    assert body["delinquentMortgages"] == 3
    assert body["delinquencyRate"] == 0.3333


def test_delinquency_highlights_mtg_1002(client):
    mortgages = client.get("/api/v1/analytics/delinquency").json()["mortgages"]
    by_id = {m["mortgageExternalId"]: m for m in mortgages}
    assert by_id["MTG-1002"] == {
        "mortgageExternalId": "MTG-1002",
        "borrowerExternalId": "BOR-002",
        "outstandingBalance": 279000.0,
        "delinquentSince": "2026-01-10",
        "daysPastDue": 45,
        "severity": "MODERATE",
    }
    assert [m["mortgageExternalId"] for m in mortgages] == ["MTG-1005", "MTG-1002", "MTG-1008"]


def test_borrower_risk(client):
    body = client.get("/api/v1/analytics/borrowers/BOR-001/risk-summary").json()
    assert body["totalMortgages"] == 2
    assert body["outstandingBalanceTotal"] == 730000.0
    assert body["riskLevel"] == "LOW"
    assert client.get("/api/v1/analytics/borrowers/BOR-004/risk-summary").json()["riskLevel"] == "HIGH"
    assert client.get("/api/v1/analytics/borrowers/BOR-999/risk-summary").status_code == 404
    export = client.get("/api/v1/analytics/borrowers/risk-summary").json()
    assert len(export["borrowers"]) == 8


def test_payment_trends_match_sql(client, engine):
    body = client.get("/api/v1/analytics/payment-trends", params={"from": "2025-01-01", "to": "2026-12-31"}).json()
    api_total = sum(b["postedAmount"] for b in body["buckets"])
    sql_total = scalar(
        engine,
        "SELECT SUM(amount) FROM payment WHERE status='POSTED' AND paid_date BETWEEN :s AND :e",
        s=date(2025, 1, 1),
        e=date(2026, 12, 31),
    )
    assert api_total == pytest.approx(float(sql_total), abs=0.005)
    jan = next(b for b in body["buckets"] if b["period"] == "2026-01")
    assert jan["onTimeRate"] == 1.0


def test_document_upload_writes_row(client, engine):
    response = client.post(
        "/api/v1/documents/upload",
        data={"mortgageExternalId": "MTG-1001", "documentType": "INCOME_VERIFICATION"},
        files={"file": ("it-paystub.pdf", b"%PDF-1.4 it", "application/pdf")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    try:
        row_key = scalar(engine, "SELECT s3_key FROM document WHERE id = :id", id=body["documentId"])
        assert row_key == body["s3Key"]
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM document WHERE id = :id"), {"id": body["documentId"]})


def test_repository_unknown_ids(engine):
    repo = MortgageRepository(engine)
    assert repo.find_mortgage_id("MTG-9999") is None
    assert repo.borrower_exists("BOR-001") is True
    assert repo.borrower_exists("BOR-999") is False


def test_startup_fails_fast_when_db_unreachable(db_settings):
    bad = Settings(**{**db_settings.__dict__, "postgres_port": 1, "db_connect_timeout_seconds": 1})
    with pytest.raises(Exception):
        with TestClient(create_app(bad, s3_client=object())):
            pass
