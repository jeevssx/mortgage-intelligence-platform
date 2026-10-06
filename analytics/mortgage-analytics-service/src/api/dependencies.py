"""FastAPI dependencies. Implementations are created once at startup and stored on app.state."""

from __future__ import annotations

from fastapi import Request

from src.services.analytics_service import AnalyticsService
from src.services.document_service import DocumentService


def get_analytics_service(request: Request) -> AnalyticsService:
    return request.app.state.analytics_service


def get_document_service(request: Request) -> DocumentService:
    return request.app.state.document_service
