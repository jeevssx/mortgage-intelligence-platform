from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from src.api.dependencies import get_analytics_service
from src.models.schemas import (
    BorrowerRiskExport,
    BorrowerRiskSummary,
    DelinquencyReport,
    ErrorResponse,
    NormalizeRequest,
    NormalizeResponse,
    PaymentTrends,
    PortfolioSummary,
)
from src.services.analytics_service import AnalyticsService

router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["analytics"],
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)

Service = Annotated[AnalyticsService, Depends(get_analytics_service)]


@router.get("/portfolio-summary", response_model=PortfolioSummary)
def portfolio_summary(service: Service) -> dict:
    return service.portfolio_summary()


@router.get("/delinquency", response_model=DelinquencyReport)
def delinquency(service: Service) -> dict:
    return service.delinquency_report()


@router.get("/borrowers/risk-summary", response_model=BorrowerRiskExport)
def all_borrower_risk(service: Service) -> dict:
    return service.all_borrower_risk()


@router.get(
    "/borrowers/{borrower_external_id}/risk-summary",
    response_model=BorrowerRiskSummary,
    responses={404: {"model": ErrorResponse}},
)
def borrower_risk_summary(
    service: Service,
    borrower_external_id: Annotated[str, Path(pattern=r"^BOR-\d{3}$", examples=["BOR-001"])],
) -> dict:
    return service.borrower_risk_summary(borrower_external_id)


@router.get("/payment-trends", response_model=PaymentTrends, response_model_by_alias=True)
def payment_trends(
    service: Service,
    from_: Annotated[date | None, Query(alias="from", description="Inclusive start (paid date)")] = None,
    to: Annotated[date | None, Query(description="Inclusive end (paid date)")] = None,
) -> dict:
    end = to or date.today()
    start = from_ or (end - timedelta(days=365))
    return service.payment_trends(start, end)


@router.post("/normalize", response_model=NormalizeResponse)
def normalize(service: Service, body: NormalizeRequest) -> dict:
    """Validate raw borrower/mortgage/payment records against the normalization rules."""
    return service.normalize_records(body.borrowers, body.mortgages, body.payments)
