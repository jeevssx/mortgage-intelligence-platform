"""PostgreSQL access for the analytics service. Reads the M2 schema; writes only `document`.

All queries use bound parameters. APIs use business IDs (MTG-####, BOR-###); internal UUIDs
stay inside this layer except for document IDs, which are returned to clients.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from typing import Protocol

import pandas as pd
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from src.config import Settings

logger = logging.getLogger(__name__)


class MortgageDataSource(Protocol):
    """Interface used by the services; lets tests substitute an in-memory fake."""

    def load_borrowers(self) -> pd.DataFrame: ...
    def load_mortgages(self) -> pd.DataFrame: ...
    def load_delinquencies(self) -> pd.DataFrame: ...
    def load_payments(self, start: date | None = None, end: date | None = None) -> pd.DataFrame: ...
    def borrower_exists(self, borrower_external_id: str) -> bool: ...
    def find_mortgage_id(self, mortgage_external_id: str) -> uuid.UUID | None: ...
    def insert_document(
        self,
        *,
        document_id: uuid.UUID,
        mortgage_id: uuid.UUID,
        document_type: str,
        s3_key: str,
        file_name: str,
    ) -> datetime: ...


def create_db_engine(settings: Settings) -> Engine:
    # Password is passed via connect_args so it never appears in the URL or in logs.
    return create_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={
            "password": settings.postgres_password,
            "connect_timeout": settings.db_connect_timeout_seconds,
            "application_name": settings.service_name,
        },
    )


class MortgageRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def check_connection(self) -> None:
        """Raise if the database is unreachable (used for fail-fast startup)."""
        with self._engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    def _frame(self, sql: str, **params: object) -> pd.DataFrame:
        with self._engine.connect() as conn:
            result = conn.execute(text(sql), params)
            return pd.DataFrame(result.fetchall(), columns=list(result.keys()))

    def load_borrowers(self) -> pd.DataFrame:
        return self._frame(
            """
            SELECT borrower_external_id, first_name, last_name, email
            FROM borrower
            ORDER BY borrower_external_id
            """
        )

    def load_mortgages(self) -> pd.DataFrame:
        return self._frame(
            """
            SELECT m.mortgage_external_id, b.borrower_external_id, m.status,
                   m.original_amount, m.outstanding_balance, m.origination_date
            FROM mortgage m
            JOIN borrower b ON b.id = m.borrower_id
            ORDER BY m.mortgage_external_id
            """
        )

    def load_delinquencies(self) -> pd.DataFrame:
        return self._frame(
            """
            SELECT m.mortgage_external_id, d.delinquent_since, d.days_past_due, d.severity
            FROM delinquency d
            JOIN mortgage m ON m.id = d.mortgage_id
            ORDER BY m.mortgage_external_id
            """
        )

    def load_payments(self, start: date | None = None, end: date | None = None) -> pd.DataFrame:
        return self._frame(
            """
            SELECT m.mortgage_external_id, p.due_date, p.paid_date, p.amount, p.status
            FROM payment p
            JOIN mortgage m ON m.id = p.mortgage_id
            WHERE (CAST(:start AS date) IS NULL OR p.paid_date >= :start OR p.paid_date IS NULL)
              AND (CAST(:end AS date) IS NULL OR p.paid_date <= :end OR p.paid_date IS NULL)
            ORDER BY m.mortgage_external_id, p.due_date
            """,
            start=start,
            end=end,
        )

    def borrower_exists(self, borrower_external_id: str) -> bool:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT 1 FROM borrower WHERE borrower_external_id = :id"),
                {"id": borrower_external_id},
            ).first()
        return row is not None

    def find_mortgage_id(self, mortgage_external_id: str) -> uuid.UUID | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT id FROM mortgage WHERE mortgage_external_id = :id"),
                {"id": mortgage_external_id},
            ).first()
        return row[0] if row else None

    def insert_document(
        self,
        *,
        document_id: uuid.UUID,
        mortgage_id: uuid.UUID,
        document_type: str,
        s3_key: str,
        file_name: str,
    ) -> datetime:
        try:
            with self._engine.begin() as conn:
                row = conn.execute(
                    text(
                        """
                        INSERT INTO document (id, mortgage_id, document_type, s3_key, file_name)
                        VALUES (:id, :mortgage_id, :document_type, :s3_key, :file_name)
                        RETURNING created_at
                        """
                    ),
                    {
                        "id": document_id,
                        "mortgage_id": mortgage_id,
                        "document_type": document_type,
                        "s3_key": s3_key,
                        "file_name": file_name,
                    },
                ).one()
        except SQLAlchemyError:
            logger.exception("Document insert failed", extra={"s3Key": s3_key})
            raise
        return row[0]
