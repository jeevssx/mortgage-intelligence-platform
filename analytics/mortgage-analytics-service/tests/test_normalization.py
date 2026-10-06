from __future__ import annotations

from datetime import date

import pytest

from src.analytics.normalization import (
    normalize_borrowers,
    normalize_mortgages,
    normalize_payments,
)
from src.utils.errors import ValidationError
from tests.conftest import read_fixture


def _mortgage(**overrides):
    row = {
        "mortgage_external_id": "MTG-1001",
        "borrower_external_id": "BOR-001",
        "status": "ACTIVE",
        "original_amount": "310000.00",
        "outstanding_balance": "305000.00",
        "origination_date": "2024-01-15",
    }
    row.update(overrides)
    return row


def _payment(**overrides):
    row = {
        "mortgage_external_id": "MTG-1001",
        "due_date": "2026-01-01",
        "paid_date": "2026-01-03",
        "amount": "1750.00",
        "status": "POSTED",
    }
    row.update(overrides)
    return row


def _errors(exc_info) -> list[dict]:
    return exc_info.value.details


class TestMortgages:
    def test_fixture_data_is_valid(self):
        result = normalize_mortgages(read_fixture("mortgages"))
        assert len(result.frame) == 7
        assert result.warnings == []

    def test_cleans_whitespace_and_case(self):
        df = normalize_mortgages(
            [_mortgage(status=" active ", mortgage_external_id="mtg-1001 ", outstanding_balance="1000.005")]
        ).frame
        assert df.loc[0, "status"] == "ACTIVE"
        assert df.loc[0, "mortgage_external_id"] == "MTG-1001"
        assert df.loc[0, "outstanding_balance"] == pytest.approx(1000.0, abs=0.01)
        assert df.loc[0, "origination_date"] == date(2024, 1, 15)

    def test_rejects_bad_status(self):
        with pytest.raises(ValidationError) as exc_info:
            normalize_mortgages([_mortgage(), _mortgage(mortgage_external_id="MTG-1002", status="LATE")])
        errors = _errors(exc_info)
        assert errors == [
            {
                "entity": "mortgage",
                "row": 1,
                "field": "status",
                "error": "'LATE' not in ['ACTIVE', 'CLOSED', 'DELINQUENT', 'FORECLOSURE', 'PENDING']",
            }
        ]

    def test_rejects_negative_balance(self):
        with pytest.raises(ValidationError) as exc_info:
            normalize_mortgages([_mortgage(outstanding_balance="-1.00")])
        assert _errors(exc_info)[0]["field"] == "outstanding_balance"
        assert "must be >= 0" in _errors(exc_info)[0]["error"]

    def test_zero_balance_is_allowed(self):
        df = normalize_mortgages([_mortgage(status="CLOSED", outstanding_balance="0")]).frame
        assert df.loc[0, "outstanding_balance"] == 0.0

    def test_rejects_non_numeric_and_non_positive_original_amount(self):
        with pytest.raises(ValidationError) as exc_info:
            normalize_mortgages(
                [_mortgage(original_amount="abc"), _mortgage(mortgage_external_id="MTG-1002", original_amount="0")]
            )
        fields = [(e["row"], e["field"]) for e in _errors(exc_info)]
        assert fields == [(0, "original_amount"), (1, "original_amount")]

    def test_rejects_bad_and_duplicate_ids(self):
        with pytest.raises(ValidationError) as exc_info:
            normalize_mortgages(
                [_mortgage(mortgage_external_id="M-1"), _mortgage(), _mortgage(borrower_external_id="B1")]
            )
        messages = {(e["row"], e["field"], e["error"].split(" ")[0]) for e in _errors(exc_info)}
        assert (0, "mortgage_external_id", "invalid") in messages
        assert (1, "mortgage_external_id", "duplicate") in messages
        assert (2, "mortgage_external_id", "duplicate") in messages
        assert (2, "borrower_external_id", "invalid") in messages

    def test_rejects_invalid_date(self):
        with pytest.raises(ValidationError) as exc_info:
            normalize_mortgages([_mortgage(origination_date="not-a-date")])
        assert _errors(exc_info)[0]["field"] == "origination_date"

    def test_collects_all_errors_in_one_pass(self):
        with pytest.raises(ValidationError) as exc_info:
            normalize_mortgages([_mortgage(status="BAD", outstanding_balance="-5")])
        assert {e["field"] for e in _errors(exc_info)} == {"status", "outstanding_balance"}
        assert exc_info.value.message == "2 invalid mortgage record(s)"


class TestPayments:
    def test_fixture_data_is_valid(self):
        df = normalize_payments(read_fixture("payments")).frame
        assert len(df) == 11
        assert df["paid_date"].isna().sum() == 3

    def test_posted_requires_paid_date(self):
        with pytest.raises(ValidationError) as exc_info:
            normalize_payments([_payment(paid_date=None)])
        assert _errors(exc_info) == [
            {"entity": "payment", "row": 0, "field": "paid_date", "error": "required when status is POSTED"}
        ]

    def test_scheduled_without_paid_date_is_fine(self):
        df = normalize_payments([_payment(status="scheduled", paid_date="")]).frame
        assert df.loc[0, "status"] == "SCHEDULED"
        assert df.loc[0, "paid_date"] is None

    def test_rejects_bad_status_amount_and_missing_due_date(self):
        with pytest.raises(ValidationError) as exc_info:
            normalize_payments([_payment(status="PAID", amount="0", due_date=None)])
        assert {e["field"] for e in _errors(exc_info)} == {"status", "amount", "due_date"}

    def test_rejects_bad_mortgage_id(self):
        with pytest.raises(ValidationError) as exc_info:
            normalize_payments([_payment(mortgage_external_id="1001")])
        assert _errors(exc_info)[0]["field"] == "mortgage_external_id"


class TestBorrowers:
    def test_missing_email_is_flagged_not_rejected(self):
        result = normalize_borrowers(read_fixture("borrowers"))
        flagged = result.frame.loc[result.frame["email_missing"], "borrower_external_id"].tolist()
        assert flagged == ["BOR-004"]
        assert result.warnings == [
            {
                "entity": "borrower",
                "row": 3,
                "field": "email",
                "warning": "missing email: row flagged and excluded from borrower risk export",
            }
        ]

    def test_email_is_lowercased(self):
        df = normalize_borrowers(
            [{"borrower_external_id": "bor-001", "first_name": " Jamie ", "last_name": "N", "email": " J@Example.TEST "}]
        ).frame
        assert df.loc[0, "email"] == "j@example.test"
        assert df.loc[0, "first_name"] == "Jamie"
        assert df.loc[0, "borrower_external_id"] == "BOR-001"

    def test_rejects_bad_borrower_id(self):
        with pytest.raises(ValidationError):
            normalize_borrowers([{"borrower_external_id": "BOR-1", "email": "x@example.test"}])
