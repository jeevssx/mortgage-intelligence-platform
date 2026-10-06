"""Loads data through the repository, normalizes it, and computes portfolio analytics."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import pandas as pd

from src.analytics import portfolio
from src.analytics.normalization import (
    normalize_borrowers,
    normalize_mortgages,
    normalize_payments,
)
from src.repositories.mortgage_repository import MortgageDataSource
from src.utils.errors import DataIntegrityError, NotFoundError, ValidationError
from src.utils.time import utc_now_iso

logger = logging.getLogger(__name__)


def _iso(value: Any) -> str | None:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


class AnalyticsService:
    def __init__(self, repository: MortgageDataSource) -> None:
        self._repo = repository

    # Data from our own database that fails normalization is a server-side integrity problem,
    # not a client error, so it is re-raised as a 500 with the details logged.
    def _mortgages(self) -> pd.DataFrame:
        try:
            return normalize_mortgages(self._repo.load_mortgages()).frame
        except ValidationError as exc:
            logger.error("Mortgage data failed normalization", extra={"issues": exc.details})
            raise DataIntegrityError("Stored mortgage data failed validation") from exc

    def _delinquencies(self) -> pd.DataFrame:
        df = self._repo.load_delinquencies()
        if df.empty:
            return pd.DataFrame(
                columns=["mortgage_external_id", "delinquent_since", "days_past_due", "severity"]
            )
        df["days_past_due"] = pd.to_numeric(df["days_past_due"]).astype(int)
        return df

    def portfolio_summary(self) -> dict[str, Any]:
        summary = portfolio.portfolio_summary(self._mortgages())
        summary["asOf"] = utc_now_iso()
        return summary

    def delinquency_report(self) -> dict[str, Any]:
        mortgages = self._mortgages()
        loans = portfolio.delinquent_loans(mortgages, self._delinquencies())
        return {
            "delinquentMortgages": int(len(loans)),
            "delinquencyRate": portfolio.delinquency_rate(mortgages),
            "delinquentBalanceTotal": round(float(loans["outstanding_balance"].sum()), 2),
            "mortgages": [
                {
                    "mortgageExternalId": row.mortgage_external_id,
                    "borrowerExternalId": row.borrower_external_id,
                    "outstandingBalance": round(float(row.outstanding_balance), 2),
                    "delinquentSince": _iso(row.delinquent_since),
                    "daysPastDue": None if pd.isna(row.days_past_due) else int(row.days_past_due),
                    "severity": None if pd.isna(row.severity) else row.severity,
                }
                for row in loans.itertuples()
            ],
            "asOf": utc_now_iso(),
        }

    @staticmethod
    def _risk_row(row: Any) -> dict[str, Any]:
        return {
            "borrowerExternalId": row.borrower_external_id,
            "totalMortgages": int(row.total_mortgages),
            "outstandingBalanceTotal": float(row.outstanding_balance_total),
            "delinquentMortgages": int(row.delinquent_mortgages),
            "delinquentBalanceTotal": float(row.delinquent_balance_total),
            "maxDaysPastDue": int(row.max_days_past_due),
            "riskLevel": row.risk_level,
        }

    def borrower_risk_summary(self, borrower_external_id: str) -> dict[str, Any]:
        mortgages = self._mortgages()
        own = mortgages[mortgages["borrower_external_id"] == borrower_external_id]
        if own.empty:
            if not self._repo.borrower_exists(borrower_external_id):
                raise NotFoundError(
                    f"Borrower {borrower_external_id} was not found", code="BORROWER_NOT_FOUND"
                )
            return {
                "borrowerExternalId": borrower_external_id,
                "totalMortgages": 0,
                "outstandingBalanceTotal": 0.0,
                "delinquentMortgages": 0,
                "delinquentBalanceTotal": 0.0,
                "maxDaysPastDue": 0,
                "riskLevel": "LOW",
                "mortgages": [],
            }
        summary = portfolio.borrower_risk_summary(own, self._delinquencies())
        result = self._risk_row(next(summary.itertuples()))
        result["mortgages"] = [
            {
                "mortgageExternalId": row.mortgage_external_id,
                "status": row.status,
                "outstandingBalance": round(float(row.outstanding_balance), 2),
            }
            for row in own.sort_values("mortgage_external_id").itertuples()
        ]
        return result

    def all_borrower_risk(self) -> dict[str, Any]:
        """Risk export for all borrowers. Borrowers flagged email_missing are excluded."""
        borrowers = normalize_borrowers(self._repo.load_borrowers()).frame
        excluded = set(borrowers.loc[borrowers["email_missing"], "borrower_external_id"])
        mortgages = self._mortgages()
        mortgages = mortgages[~mortgages["borrower_external_id"].isin(excluded)]
        summary = portfolio.borrower_risk_summary(mortgages, self._delinquencies())
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        summary = summary.sort_values(
            by=["risk_level", "outstanding_balance_total"],
            key=lambda s: s.map(order) if s.name == "risk_level" else -s,
        )
        return {
            "borrowers": [self._risk_row(row) for row in summary.itertuples()],
            "excludedBorrowers": sorted(excluded),
            "asOf": utc_now_iso(),
        }

    def payment_trends(self, start: date, end: date) -> dict[str, Any]:
        if start > end:
            raise ValidationError("'from' must be on or before 'to'")
        try:
            payments = normalize_payments(self._repo.load_payments(start, end)).frame
        except ValidationError as exc:
            logger.error("Payment data failed normalization", extra={"issues": exc.details})
            raise DataIntegrityError("Stored payment data failed validation") from exc
        buckets = portfolio.payment_trends(payments, start, end)
        return {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "buckets": [
                {
                    "period": row.period,
                    "postedAmount": float(row.posted_amount),
                    "paymentCount": int(row.payment_count),
                    "onTimeRate": float(row.on_time_rate),
                }
                for row in buckets.itertuples()
            ],
        }

    @staticmethod
    def normalize_records(
        borrowers: list[dict[str, Any]],
        mortgages: list[dict[str, Any]],
        payments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Validate client-supplied records. Raises ValidationError (HTTP 400) on any invalid row."""
        errors: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        counts: dict[str, int] = {}
        for name, records, fn in (
            ("borrowers", borrowers, normalize_borrowers),
            ("mortgages", mortgages, normalize_mortgages),
            ("payments", payments, normalize_payments),
        ):
            if not records:
                counts[name] = 0
                continue
            try:
                result = fn(records)
            except ValidationError as exc:
                errors.extend(exc.details or [])
                continue
            counts[name] = int(len(result.frame))
            warnings.extend(result.warnings)
        if errors:
            raise ValidationError(f"{len(errors)} validation error(s)", details=errors)
        return {"valid": True, "counts": counts, "warnings": warnings}
