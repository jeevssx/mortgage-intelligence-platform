"""Portfolio analytics over normalized DataFrames (see README "Metric formulas")."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

ON_TIME_GRACE_DAYS = 15
SERVICED_STATUSES = ("ACTIVE", "DELINQUENT")


def _money(value: float) -> float:
    return round(float(value), 2)


def delinquency_rate(mortgages: pd.DataFrame) -> float:
    """count(DELINQUENT) / count(ACTIVE + DELINQUENT); 0.0 when nothing is being serviced."""
    serviced = mortgages["status"].isin(SERVICED_STATUSES).sum()
    if serviced == 0:
        return 0.0
    delinquent = (mortgages["status"] == "DELINQUENT").sum()
    return round(float(delinquent / serviced), 4)


def portfolio_summary(mortgages: pd.DataFrame) -> dict[str, float | int]:
    status = mortgages["status"]
    serviced = mortgages[status.isin(SERVICED_STATUSES)]
    delinquent = mortgages[status == "DELINQUENT"]
    return {
        "totalMortgages": int(len(mortgages)),
        "activeMortgages": int((status == "ACTIVE").sum()),
        "delinquentMortgages": int(len(delinquent)),
        "pendingMortgages": int((status == "PENDING").sum()),
        "closedMortgages": int((status == "CLOSED").sum()),
        "outstandingBalanceTotal": _money(serviced["outstanding_balance"].sum()),
        "delinquentBalanceTotal": _money(delinquent["outstanding_balance"].sum()),
        "delinquencyRate": delinquency_rate(mortgages),
    }


def delinquent_loans(mortgages: pd.DataFrame, delinquencies: pd.DataFrame) -> pd.DataFrame:
    """Delinquent mortgages joined to their delinquency snapshot, worst first."""
    delinquent = mortgages[mortgages["status"] == "DELINQUENT"]
    merged = delinquent.merge(delinquencies, on="mortgage_external_id", how="left")
    merged = merged.sort_values(
        ["days_past_due", "mortgage_external_id"], ascending=[False, True], na_position="last"
    )
    return merged[
        [
            "mortgage_external_id",
            "borrower_external_id",
            "outstanding_balance",
            "delinquent_since",
            "days_past_due",
            "severity",
        ]
    ].reset_index(drop=True)


def _risk_level(row: pd.Series) -> str:
    if row["delinquent_mortgages"] == 0:
        return "LOW"
    if row["max_days_past_due"] >= 60:
        return "HIGH"
    return "MEDIUM"


def borrower_risk_summary(mortgages: pd.DataFrame, delinquencies: pd.DataFrame) -> pd.DataFrame:
    """One row per borrower: exposure, delinquent count/balance, worst days past due, risk level.

    Only serviced mortgages (ACTIVE, DELINQUENT) count toward balances; total_mortgages counts all.
    """
    df = mortgages.merge(
        delinquencies[["mortgage_external_id", "days_past_due"]], on="mortgage_external_id", how="left"
    )
    df["is_delinquent"] = df["status"] == "DELINQUENT"
    df["serviced_balance"] = df["outstanding_balance"].where(df["status"].isin(SERVICED_STATUSES), 0.0)
    df["delinquent_balance"] = df["outstanding_balance"].where(df["is_delinquent"], 0.0)
    df["days_past_due"] = df["days_past_due"].where(df["is_delinquent"], 0).fillna(0)

    summary = (
        df.groupby("borrower_external_id", sort=True)
        .agg(
            total_mortgages=("mortgage_external_id", "count"),
            outstanding_balance_total=("serviced_balance", "sum"),
            delinquent_mortgages=("is_delinquent", "sum"),
            delinquent_balance_total=("delinquent_balance", "sum"),
            max_days_past_due=("days_past_due", "max"),
        )
        .reset_index()
    )
    summary["delinquent_mortgages"] = summary["delinquent_mortgages"].astype(int)
    summary["max_days_past_due"] = summary["max_days_past_due"].astype(int)
    summary["outstanding_balance_total"] = summary["outstanding_balance_total"].round(2)
    summary["delinquent_balance_total"] = summary["delinquent_balance_total"].round(2)
    summary["risk_level"] = summary.apply(_risk_level, axis=1)
    return summary


def payment_trends(payments: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Monthly buckets of POSTED payments by paid_date within [start, end].

    on_time_rate = share of posted payments with paid_date <= due_date + 15 days.
    Months with no posted payments are omitted.
    """
    columns = ["period", "posted_amount", "payment_count", "on_time_rate"]
    posted = payments[payments["status"] == "POSTED"].copy()
    if posted.empty:
        return pd.DataFrame(columns=columns)
    posted["paid_date"] = pd.to_datetime(posted["paid_date"])
    posted["due_date"] = pd.to_datetime(posted["due_date"])
    posted = posted[(posted["paid_date"] >= pd.Timestamp(start)) & (posted["paid_date"] <= pd.Timestamp(end))]
    if posted.empty:
        return pd.DataFrame(columns=columns)
    posted["on_time"] = posted["paid_date"] <= posted["due_date"] + timedelta(days=ON_TIME_GRACE_DAYS)

    buckets = (
        posted.groupby(pd.Grouper(key="paid_date", freq="MS"))
        .agg(posted_amount=("amount", "sum"), payment_count=("amount", "count"), on_time=("on_time", "mean"))
        .reset_index()
    )
    buckets = buckets[buckets["payment_count"] > 0]
    buckets["period"] = buckets["paid_date"].dt.strftime("%Y-%m")
    buckets["posted_amount"] = buckets["posted_amount"].round(2)
    buckets["payment_count"] = buckets["payment_count"].astype(int)
    buckets["on_time_rate"] = buckets["on_time"].round(4)
    return buckets[columns].reset_index(drop=True)
