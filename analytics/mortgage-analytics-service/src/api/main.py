"""FastAPI app factory.

Run: uvicorn src.api.main:app --reload --port 8000
Tests call create_app(...) with fakes, so no database or AWS is needed.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI

from src.api.middleware import CorrelationIdMiddleware, register_exception_handlers
from src.api.routes import analytics, documents, health
from src.config import Settings, get_settings
from src.repositories.mortgage_repository import MortgageDataSource, MortgageRepository, create_db_engine
from src.services.analytics_service import AnalyticsService
from src.services.aws_clients import create_s3_client, create_sns_client
from src.services.document_service import DocumentService
from src.utils.logging_config import configure_logging

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    repository: MortgageDataSource | None = None,
    s3_client: Any | None = None,
    sns_client: Any | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.service_name, settings.log_level)

    engine = None
    if repository is None:
        engine = create_db_engine(settings)
        repository = MortgageRepository(engine)
    s3_client = s3_client if s3_client is not None else create_s3_client(settings)
    if sns_client is None:
        sns_client = create_sns_client(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if settings.db_check_on_startup and isinstance(repository, MortgageRepository):
            try:
                repository.check_connection()
            except Exception as exc:
                logger.critical(
                    "Database unreachable at startup; refusing to start",
                    extra={"host": settings.postgres_host, "db": settings.postgres_db, "error": type(exc).__name__},
                )
                raise
            logger.info("Database connection verified", extra={"host": settings.postgres_host})
        logger.info("Service started")
        yield
        if engine is not None:
            engine.dispose()

    app = FastAPI(
        title="Mortgage Analytics Service",
        version="1.0.0",
        description="Portfolio analytics, normalization, and document upload for the Mortgage Intelligence Platform.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.analytics_service = AnalyticsService(repository)
    app.state.document_service = DocumentService(repository, s3_client, settings, sns_client)

    app.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(analytics.router)
    app.include_router(documents.router)
    return app


def __getattr__(name: str) -> FastAPI:
    # Lazily build `app` so importing this module (e.g. in tests) doesn't connect to anything.
    if name == "app":
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(name)
