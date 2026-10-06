"""Normalize and validate borrower, mortgage, and payment records into typed DataFrames.

Rules (see README "Normalization rules"):
- status values must be in the enums from the engineering standards
- outstanding_balance >= 0, original_amount > 0, payment amount > 0
- POSTED payments must have a paid_date
- business IDs must match BOR-###, MTG-####
- a missing borrower email is a warning, not an error: the row is flagged (email_missing)
  and excluded from the borrower risk export
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

import pandas as pd

from src.utils.errors import ValidationError

logger = logging.getLogger(__name__)

MORTGAGE_STATUSES = frozenset({"PENDING", "ACTIVE", "DELINQUENT", "CLOSED", "FORECLOSURE"})
PAYMENT_STATUSES = frozenset({"SCHEDULED", "POSTED", "FAILED", "REVERSED"})

BORROWER_ID_RE = re.compile(r"^BOR-\d{3}$")
MORTGAGE_ID_RE = re.compile(r"^MTG-\d{4}$")

BORROWER_COLUMNS = ["borrower_external_id", "first_name", "last_name", "email"]
MORTGAGE_COLUMNS = [
    "mortgage_external_id",
    "borrower_external_id",
    "status",
    "original_amount",
    "outstanding_balance",
    "origination_date",
]
PAYMENT_COLUMNS = ["mortgage_external_id", "due_date", "paid_date", "amount", "status"]


@dataclass
class NormalizationResult:
    frame: pd.DataFrame
    warnings: list[dict[str, Any]] = field(default_factory=list)


class _Issues:
    def __init__(self, entity: str) -> None:
        self.entity = entity
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def error(self, row: Any, column: str, message: str) -> None:
        self.errors.append({"entity": self.entity, "row": _row_ref(row), "field": column, "error": message})

    def warn(self, row: Any, column: str, message: str) -> None:
        self.warnings.append({"entity": self.entity, "row": _row_ref(row), "field": column, "warning": message})

    def finish(self) -> list[dict[str, Any]]:
        for w in self.warnings:
            logger.warning("Normalization warning", extra={"validation": w})
        if self.errors:
            raise ValidationError(
                f"{len(self.errors)} invalid {self.entity} record(s)",
                details=self.errors,
            )
        return self.warnings


def _row_ref(row: Any) -> Any:
    return int(row) if hasattr(row, "__index__") else row


def _to_frame(records: pd.DataFrame | Iterable[dict[str, Any]], columns: list[str]) -> pd.DataFrame:
    df = records.copy() if isinstance(records, pd.DataFrame) else pd.DataFrame(list(records))
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df.reset_index(drop=True)


def _clean_str(series: pd.Series, *, upper: bool = False, lower: bool = False) -> pd.Series:
    def clean(value: Any) -> Any:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        text = str(value).strip()
        if not text:
            return None
        if upper:
            return text.upper()
        if lower:
            return text.lower()
        return text

    return series.map(clean).astype(object)


def _check_ids(df: pd.DataFrame, column: str, pattern: re.Pattern[str], issues: _Issues) -> None:
    for idx, value in df[column].items():
        if value is None or not pattern.match(value):
            issues.error(idx, column, f"invalid id {value!r}")
    dupes = df[column][df[column].notna() & df[column].duplicated(keep=False)]
    for idx, value in dupes.items():
        issues.error(idx, column, f"duplicate id {value!r}")


def _to_date(series: pd.Series, column: str, issues: _Issues, *, required: bool) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    for idx in series.index:
        raw = series[idx]
        missing = raw is None or (isinstance(raw, float) and pd.isna(raw)) or raw == ""
        if missing:
            if required:
                issues.error(idx, column, "required")
        elif pd.isna(parsed[idx]):
            issues.error(idx, column, f"invalid date {raw!r}")
    return parsed.dt.date.astype(object).where(parsed.notna(), None)


def _to_money(series: pd.Series, column: str, issues: _Issues, *, minimum: float, strict: bool) -> pd.Series:
    numbers = pd.to_numeric(series.map(lambda v: None if v is None else str(v)), errors="coerce")
    for idx, value in numbers.items():
        if pd.isna(value):
            issues.error(idx, column, f"not a number: {series[idx]!r}")
        elif (strict and value <= minimum) or (not strict and value < minimum):
            op = ">" if strict else ">="
            issues.error(idx, column, f"must be {op} {minimum:g}, got {value:g}")
    return numbers.astype(float).round(2)


def _check_enum(series: pd.Series, column: str, allowed: frozenset[str], issues: _Issues) -> None:
    for idx, value in series.items():
        if value not in allowed:
            issues.error(idx, column, f"{value!r} not in {sorted(allowed)}")


def normalize_borrowers(records: pd.DataFrame | Iterable[dict[str, Any]]) -> NormalizationResult:
    issues = _Issues("borrower")
    df = _to_frame(records, BORROWER_COLUMNS)
    df["borrower_external_id"] = _clean_str(df["borrower_external_id"], upper=True)
    df["first_name"] = _clean_str(df["first_name"])
    df["last_name"] = _clean_str(df["last_name"])
    df["email"] = _clean_str(df["email"], lower=True)
    _check_ids(df, "borrower_external_id", BORROWER_ID_RE, issues)

    df["email_missing"] = df["email"].isna()
    for idx in df.index[df["email_missing"]]:
        issues.warn(idx, "email", "missing email: row flagged and excluded from borrower risk export")

    return NormalizationResult(df, issues.finish())


def normalize_mortgages(records: pd.DataFrame | Iterable[dict[str, Any]]) -> NormalizationResult:
    issues = _Issues("mortgage")
    df = _to_frame(records, MORTGAGE_COLUMNS)
    df["mortgage_external_id"] = _clean_str(df["mortgage_external_id"], upper=True)
    df["borrower_external_id"] = _clean_str(df["borrower_external_id"], upper=True)
    df["status"] = _clean_str(df["status"], upper=True)
    _check_ids(df, "mortgage_external_id", MORTGAGE_ID_RE, issues)
    for idx, value in df["borrower_external_id"].items():
        if value is None or not BORROWER_ID_RE.match(value):
            issues.error(idx, "borrower_external_id", f"invalid id {value!r}")
    _check_enum(df["status"], "status", MORTGAGE_STATUSES, issues)
    df["original_amount"] = _to_money(df["original_amount"], "original_amount", issues, minimum=0, strict=True)
    df["outstanding_balance"] = _to_money(
        df["outstanding_balance"], "outstanding_balance", issues, minimum=0, strict=False
    )
    df["origination_date"] = _to_date(df["origination_date"], "origination_date", issues, required=False)
    return NormalizationResult(df, issues.finish())


def normalize_payments(records: pd.DataFrame | Iterable[dict[str, Any]]) -> NormalizationResult:
    issues = _Issues("payment")
    df = _to_frame(records, PAYMENT_COLUMNS)
    df["mortgage_external_id"] = _clean_str(df["mortgage_external_id"], upper=True)
    df["status"] = _clean_str(df["status"], upper=True)
    for idx, value in df["mortgage_external_id"].items():
        if value is None or not MORTGAGE_ID_RE.match(value):
            issues.error(idx, "mortgage_external_id", f"invalid id {value!r}")
    _check_enum(df["status"], "status", PAYMENT_STATUSES, issues)
    df["due_date"] = _to_date(df["due_date"], "due_date", issues, required=True)
    df["paid_date"] = _to_date(df["paid_date"], "paid_date", issues, required=False)
    df["amount"] = _to_money(df["amount"], "amount", issues, minimum=0, strict=True)
    posted_without_date = (df["status"] == "POSTED") & df["paid_date"].isna()
    for idx in df.index[posted_without_date]:
        issues.error(idx, "paid_date", "required when status is POSTED")
    return NormalizationResult(df, issues.finish())
