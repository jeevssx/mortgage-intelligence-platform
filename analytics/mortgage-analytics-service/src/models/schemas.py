"""Pydantic request/response models. JSON field names are camelCase per the API contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    code: str
    message: str
    correlationId: str | None
    timestamp: str
    details: list[dict[str, Any]] | None = None


class HealthResponse(BaseModel):
    status: Literal["UP"]
    service: str


class PortfolioSummary(BaseModel):
    totalMortgages: int
    activeMortgages: int
    delinquentMortgages: int
    pendingMortgages: int
    closedMortgages: int
    outstandingBalanceTotal: float = Field(description="Sum of outstanding_balance for ACTIVE + DELINQUENT")
    delinquentBalanceTotal: float
    delinquencyRate: float = Field(description="DELINQUENT / (ACTIVE + DELINQUENT), 4 decimals")
    asOf: str


class DelinquentMortgage(BaseModel):
    mortgageExternalId: str
    borrowerExternalId: str
    outstandingBalance: float
    delinquentSince: str | None
    daysPastDue: int | None
    severity: str | None


class DelinquencyReport(BaseModel):
    delinquentMortgages: int
    delinquencyRate: float
    delinquentBalanceTotal: float
    mortgages: list[DelinquentMortgage]
    asOf: str


class BorrowerMortgage(BaseModel):
    mortgageExternalId: str
    status: str
    outstandingBalance: float


class BorrowerRisk(BaseModel):
    borrowerExternalId: str
    totalMortgages: int
    outstandingBalanceTotal: float
    delinquentMortgages: int
    delinquentBalanceTotal: float
    maxDaysPastDue: int
    riskLevel: Literal["LOW", "MEDIUM", "HIGH"]


class BorrowerRiskSummary(BorrowerRisk):
    mortgages: list[BorrowerMortgage]


class BorrowerRiskExport(BaseModel):
    borrowers: list[BorrowerRisk]
    excludedBorrowers: list[str] = Field(description="Borrowers flagged by normalization (e.g. missing email)")
    asOf: str


class PaymentTrendBucket(BaseModel):
    period: str = Field(examples=["2026-01"])
    postedAmount: float
    paymentCount: int
    onTimeRate: float


class PaymentTrends(BaseModel):
    from_: str = Field(alias="from")
    to: str
    buckets: list[PaymentTrendBucket]

    model_config = {"populate_by_name": True}


class NormalizeRequest(BaseModel):
    """Raw records (snake_case keys, as in the database) to validate."""

    borrowers: list[dict[str, Any]] = Field(default_factory=list)
    mortgages: list[dict[str, Any]] = Field(default_factory=list)
    payments: list[dict[str, Any]] = Field(default_factory=list)


class NormalizeResponse(BaseModel):
    valid: bool
    counts: dict[str, int]
    warnings: list[dict[str, Any]]


class DocumentUploadJson(BaseModel):
    mortgageExternalId: str
    documentType: str
    fileName: str
    contentBase64: str
    contentType: str | None = None


class DocumentUploadResponse(BaseModel):
    documentId: str
    mortgageExternalId: str
    documentType: str
    fileName: str
    s3Key: str
    sizeBytes: int
    uploadedAt: str
    correlationId: str | None
