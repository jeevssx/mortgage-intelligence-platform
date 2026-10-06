"""Analytics over the CSV fixtures, whose expected values are worked out by hand:

mortgages: 4 ACTIVE, 1 DELINQUENT (MTG-1002), 1 PENDING, 1 CLOSED
delinquency rate = 1 / (4 + 1) = 0.2
serviced balance = 305000 + 279000 + 425000 + 318400 + 178900 = 1,506,300.00
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src.analytics import portfolio
from src.analytics.normalization import normalize_mortgages, normalize_payments
from src.services.analytics_service import AnalyticsService
from src.utils.errors import DataIntegrityError, NotFoundError, ValidationError
from tests.conftest import FakeRepository, read_fixture


@pytest.fixture
def mortgages() -> pd.DataFrame:
    return normalize_mortgages(read_fixture("mortgages")).frame


@pytest.fixture
def delinquencies() -> pd.DataFrame:
    df = read_fixture("delinquencies")
    df["days_past_due"] = df["days_past_due"].astype(int)
    return df


@pytest.fixture
def payments() -> pd.DataFrame:
    return normalize_payments(read_fixture("payments")).frame


def test_delinquency_rate_known_value(mortgages):
    assert portfolio.delinquency_rate(mortgages) == 0.2


def test_delinquency_rate_excludes_pending_and_closed():
    df = pd.DataFrame({"status": ["DELINQUENT", "PENDING", "CLOSED", "CLOSED"], "outstanding_balance": [1.0] * 4})
    assert portfolio.delinquency_rate(df) == 1.0


def test_delinquency_rate_is_zero_when_nothing_serviced():
    df = pd.DataFrame({"status": ["PENDING", "CLOSED"], "outstanding_balance": [1.0, 0.0]})
    assert portfolio.delinquency_rate(df) == 0.0


def test_portfolio_summary(mortgages):
    assert portfolio.portfolio_summary(mortgages) == {
        "totalMortgages": 7,
        "activeMortgages": 4,
        "delinquentMortgages": 1,
        "pendingMortgages": 1,
        "closedMortgages": 1,
        "outstandingBalanceTotal": 1506300.00,
        "delinquentBalanceTotal": 279000.00,
        "delinquencyRate": 0.2,
    }


def test_delinquent_loans_joins_snapshot_worst_first(mortgages, delinquencies):
    extra = mortgages.iloc[[0]].assign(mortgage_external_id="MTG-1099", status="DELINQUENT")
    df = pd.concat([mortgages, extra], ignore_index=True)
    snap = pd.concat(
        [delinquencies, pd.DataFrame([{"mortgage_external_id": "MTG-1099", "delinquent_since": "2025-11-01",
                                        "days_past_due": 90, "severity": "SEVERE"}])],
        ignore_index=True,
    )
    loans = portfolio.delinquent_loans(df, snap)
    assert loans["mortgage_external_id"].tolist() == ["MTG-1099", "MTG-1002"]
    assert loans.loc[1, "days_past_due"] == 45
    assert loans.loc[1, "severity"] == "MODERATE"


def test_borrower_risk_summary(mortgages, delinquencies):
    summary = portfolio.borrower_risk_summary(mortgages, delinquencies).set_index("borrower_external_id")
    bor2 = summary.loc["BOR-002"]
    assert bor2["total_mortgages"] == 2  # includes the PENDING mortgage
    assert bor2["outstanding_balance_total"] == 279000.00  # PENDING balance is not serviced exposure
    assert bor2["delinquent_mortgages"] == 1
    assert bor2["max_days_past_due"] == 45
    assert bor2["risk_level"] == "MEDIUM"
    assert summary.loc["BOR-001", "outstanding_balance_total"] == 730000.00
    assert summary.loc["BOR-001", "risk_level"] == "LOW"
    assert summary.loc["BOR-004", "outstanding_balance_total"] == 178900.00  # CLOSED contributes 0


def test_borrower_risk_high_at_60_days(mortgages, delinquencies):
    delinquencies.loc[0, "days_past_due"] = 60
    summary = portfolio.borrower_risk_summary(mortgages, delinquencies).set_index("borrower_external_id")
    assert summary.loc["BOR-002", "risk_level"] == "HIGH"


def test_payment_trends_monthly_buckets(payments):
    trends = portfolio.payment_trends(payments, date(2025, 1, 1), date(2026, 12, 31))
    assert trends.to_dict("records") == [
        # MTG-1002 on time; MTG-1004 paid 19 days after due (outside 15-day grace)
        {"period": "2025-12", "posted_amount": 3800.00, "payment_count": 2, "on_time_rate": 0.5},
        {"period": "2026-01", "posted_amount": 5265.00, "payment_count": 3, "on_time_rate": 1.0},
        # REVERSED payment excluded; re-posted payment 8 days after due is on time
        {"period": "2026-02", "posted_amount": 3115.00, "payment_count": 2, "on_time_rate": 1.0},
    ]


def test_payment_trends_respects_range(payments):
    trends = portfolio.payment_trends(payments, date(2026, 1, 1), date(2026, 1, 31))
    assert trends["period"].tolist() == ["2026-01"]


def test_payment_trends_empty(payments):
    assert portfolio.payment_trends(payments, date(2020, 1, 1), date(2020, 12, 31)).empty
    assert portfolio.payment_trends(payments.iloc[0:0], date(2020, 1, 1), date(2030, 1, 1)).empty


class TestAnalyticsService:
    def test_portfolio_summary_has_as_of(self):
        result = AnalyticsService(FakeRepository()).portfolio_summary()
        assert result["delinquencyRate"] == 0.2
        assert result["asOf"].endswith("Z")

    def test_delinquency_report(self):
        report = AnalyticsService(FakeRepository()).delinquency_report()
        assert report["delinquentMortgages"] == 1
        assert report["mortgages"] == [
            {
                "mortgageExternalId": "MTG-1002",
                "borrowerExternalId": "BOR-002",
                "outstandingBalance": 279000.00,
                "delinquentSince": "2026-01-10",
                "daysPastDue": 45,
                "severity": "MODERATE",
            }
        ]

    def test_delinquency_report_without_snapshot_rows(self):
        repo = FakeRepository()
        repo.delinquencies = repo.delinquencies.iloc[0:0]
        report = AnalyticsService(repo).delinquency_report()
        assert report["mortgages"][0]["daysPastDue"] is None
        assert report["mortgages"][0]["severity"] is None

    def test_borrower_risk_unknown_borrower(self):
        with pytest.raises(NotFoundError) as exc_info:
            AnalyticsService(FakeRepository()).borrower_risk_summary("BOR-999")
        assert exc_info.value.code == "BORROWER_NOT_FOUND"

    def test_borrower_risk_borrower_without_mortgages(self):
        repo = FakeRepository()
        repo.borrowers.loc[len(repo.borrowers)] = ["BOR-005", "A", "B", "a@example.test"]
        result = AnalyticsService(repo).borrower_risk_summary("BOR-005")
        assert result["totalMortgages"] == 0
        assert result["riskLevel"] == "LOW"

    def test_all_borrower_risk_excludes_missing_email_and_sorts(self):
        result = AnalyticsService(FakeRepository()).all_borrower_risk()
        assert result["excludedBorrowers"] == ["BOR-004"]
        ids = [b["borrowerExternalId"] for b in result["borrowers"]]
        assert ids == ["BOR-002", "BOR-001", "BOR-003"]  # MEDIUM first, then LOW by balance desc

    def test_payment_trends_rejects_inverted_range(self):
        with pytest.raises(ValidationError):
            AnalyticsService(FakeRepository()).payment_trends(date(2026, 2, 1), date(2026, 1, 1))

    def test_bad_stored_data_is_integrity_error(self):
        repo = FakeRepository()
        repo.mortgages.loc[0, "status"] = "BOGUS"
        with pytest.raises(DataIntegrityError):
            AnalyticsService(repo).portfolio_summary()

    def test_bad_stored_payment_is_integrity_error(self):
        repo = FakeRepository()
        repo.payments.loc[0, "paid_date"] = None
        with pytest.raises(DataIntegrityError):
            AnalyticsService(repo).payment_trends(date(2025, 1, 1), date(2026, 12, 31))
