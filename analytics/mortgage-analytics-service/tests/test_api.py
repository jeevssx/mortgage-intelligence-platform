from __future__ import annotations

import json
import re

from fastapi.testclient import TestClient

from src.api.main import create_app
from tests.conftest import FakeRepository, NoAwsClient

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
ISO_Z_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def assert_error_envelope(response, status: int, code: str) -> dict:
    assert response.status_code == status, response.text
    body = response.json()
    assert body["code"] == code
    assert body["message"]
    assert body["correlationId"] == response.headers["X-Correlation-Id"]
    assert ISO_Z_RE.match(body["timestamp"])
    return body


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "UP", "service": "mortgage-analytics-service"}


def test_portfolio_summary(client):
    response = client.get("/api/v1/analytics/portfolio-summary")
    assert response.status_code == 200
    body = response.json()
    assert body["totalMortgages"] == 7
    assert body["delinquentMortgages"] >= 1
    assert body["delinquencyRate"] == 0.2
    assert body["outstandingBalanceTotal"] == 1506300.00
    assert ISO_Z_RE.match(body["asOf"])


def test_delinquency_highlights_mtg_1002(client):
    body = client.get("/api/v1/analytics/delinquency").json()
    assert [m["mortgageExternalId"] for m in body["mortgages"]] == ["MTG-1002"]
    assert body["mortgages"][0]["daysPastDue"] == 45


def test_borrower_risk_summary(client):
    body = client.get("/api/v1/analytics/borrowers/BOR-002/risk-summary").json()
    assert body["delinquentMortgages"] == 1
    assert body["riskLevel"] == "MEDIUM"
    assert [m["mortgageExternalId"] for m in body["mortgages"]] == ["MTG-1002", "MTG-1009"]


def test_borrower_risk_not_found(client):
    response = client.get("/api/v1/analytics/borrowers/BOR-999/risk-summary")
    assert_error_envelope(response, 404, "BORROWER_NOT_FOUND")


def test_borrower_risk_bad_id_is_400(client):
    response = client.get("/api/v1/analytics/borrowers/not-an-id/risk-summary")
    assert_error_envelope(response, 400, "VALIDATION_ERROR")


def test_all_borrowers_risk(client):
    body = client.get("/api/v1/analytics/borrowers/risk-summary").json()
    assert body["excludedBorrowers"] == ["BOR-004"]
    assert len(body["borrowers"]) == 3


def test_payment_trends(client):
    response = client.get("/api/v1/analytics/payment-trends", params={"from": "2025-01-01", "to": "2026-12-31"})
    assert response.status_code == 200
    body = response.json()
    assert body["from"] == "2025-01-01" and body["to"] == "2026-12-31"
    assert [b["period"] for b in body["buckets"]] == ["2025-12", "2026-01", "2026-02"]
    assert body["buckets"][0] == {"period": "2025-12", "postedAmount": 3800.0, "paymentCount": 2, "onTimeRate": 0.5}


def test_payment_trends_defaults_to_last_year(client):
    body = client.get("/api/v1/analytics/payment-trends", params={"to": "2026-02-28"}).json()
    assert body["from"] == "2025-02-28"


def test_payment_trends_inverted_range_is_400(client):
    response = client.get("/api/v1/analytics/payment-trends", params={"from": "2026-12-31", "to": "2025-01-01"})
    assert_error_envelope(response, 400, "VALIDATION_ERROR")


def test_payment_trends_bad_date_is_400(client):
    response = client.get("/api/v1/analytics/payment-trends", params={"from": "yesterday"})
    body = assert_error_envelope(response, 400, "VALIDATION_ERROR")
    assert body["details"][0]["field"] == "query.from"


def test_normalize_valid(client):
    response = client.post(
        "/api/v1/analytics/normalize",
        json={"borrowers": [{"borrower_external_id": "BOR-009", "first_name": "A", "last_name": "B", "email": ""}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["counts"] == {"borrowers": 1, "mortgages": 0, "payments": 0}
    assert body["warnings"][0]["field"] == "email"


def test_normalize_invalid_is_400_with_details(client):
    response = client.post(
        "/api/v1/analytics/normalize",
        json={
            "mortgages": [
                {"mortgage_external_id": "MTG-2001", "borrower_external_id": "BOR-001", "status": "LATE",
                 "original_amount": 100, "outstanding_balance": -1}
            ],
            "payments": [{"mortgage_external_id": "MTG-2001", "due_date": "2026-01-01", "amount": 10, "status": "POSTED"}],
        },
    )
    body = assert_error_envelope(response, 400, "VALIDATION_ERROR")
    assert {(d["entity"], d["field"]) for d in body["details"]} == {
        ("mortgage", "status"),
        ("mortgage", "outstanding_balance"),
        ("payment", "paid_date"),
    }


def test_unknown_route_uses_envelope(client):
    assert_error_envelope(client.get("/api/v1/nope"), 404, "NOT_FOUND")


def test_correlation_id_is_echoed(client):
    response = client.get("/health", headers={"X-Correlation-Id": "demo-m3-001"})
    assert response.headers["X-Correlation-Id"] == "demo-m3-001"


def test_correlation_id_generated_when_missing(client):
    assert UUID_RE.match(client.get("/health").headers["X-Correlation-Id"])


def test_unsafe_correlation_id_is_replaced(client):
    response = client.get("/health", headers={"X-Correlation-Id": "bad id\twith spaces"})
    assert UUID_RE.match(response.headers["X-Correlation-Id"])


def test_logs_are_json_with_correlation_id(settings, repo, capsys):
    app = create_app(settings, repository=repo, s3_client=NoAwsClient())
    with TestClient(app) as client:
        client.get("/api/v1/analytics/portfolio-summary", headers={"X-Correlation-Id": "demo-m3-001"})
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    request_logs = [l for l in lines if l["message"] == "Request completed"]
    assert request_logs, lines
    entry = request_logs[-1]
    assert entry["correlationId"] == "demo-m3-001"
    assert entry["service"] == "mortgage-analytics-service"
    assert entry["level"] == "INFO"
    assert entry["path"] == "/api/v1/analytics/portfolio-summary"
    assert entry["status"] == 200


def test_unexpected_error_is_500_without_stack_trace(settings):
    class Broken(FakeRepository):
        def load_mortgages(self):
            raise RuntimeError("secret internal detail")

    app = create_app(settings, repository=Broken(), s3_client=NoAwsClient())
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/analytics/portfolio-summary")
    body = assert_error_envelope(response, 500, "INTERNAL_ERROR")
    assert "secret" not in response.text
    assert "Traceback" not in response.text
    assert body["message"] == "An unexpected error occurred"


def test_integrity_error_is_500(settings):
    repo = FakeRepository()
    repo.mortgages.loc[0, "outstanding_balance"] = "-1"
    app = create_app(settings, repository=repo, s3_client=NoAwsClient())
    with TestClient(app) as client:
        assert_error_envelope(client.get("/api/v1/analytics/portfolio-summary"), 500, "DATA_INTEGRITY_ERROR")
