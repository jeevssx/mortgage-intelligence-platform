from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.config import Settings

FIXTURES = Path(__file__).parent / "fixtures"
TEST_BUCKET = "capstone-mortgage-docs-test"


def read_fixture(name: str) -> pd.DataFrame:
    # keep_default_na=False + replace("") mimics NULLs coming back from the database as None
    df = pd.read_csv(FIXTURES / f"{name}.csv", dtype=str, keep_default_na=False)
    return df.replace({"": None}).astype(object)


class FakeRepository:
    """In-memory stand-in for MortgageRepository backed by the CSV fixtures."""

    def __init__(self) -> None:
        self.borrowers = read_fixture("borrowers")
        self.mortgages = read_fixture("mortgages")
        self.delinquencies = read_fixture("delinquencies")
        self.payments = read_fixture("payments")
        self.documents: list[dict] = []
        self.fail_insert = False

    def load_borrowers(self) -> pd.DataFrame:
        return self.borrowers.copy()

    def load_mortgages(self) -> pd.DataFrame:
        return self.mortgages.copy()

    def load_delinquencies(self) -> pd.DataFrame:
        return self.delinquencies.copy()

    def load_payments(self, start: date | None = None, end: date | None = None) -> pd.DataFrame:
        return self.payments.copy()

    def borrower_exists(self, borrower_external_id: str) -> bool:
        return borrower_external_id in set(self.borrowers["borrower_external_id"])

    def find_mortgage_id(self, mortgage_external_id: str) -> uuid.UUID | None:
        if mortgage_external_id in set(self.mortgages["mortgage_external_id"]):
            return uuid.uuid5(uuid.NAMESPACE_URL, mortgage_external_id)
        return None

    def insert_document(self, **row: object) -> datetime:
        if self.fail_insert:
            from sqlalchemy.exc import OperationalError

            raise OperationalError("INSERT", {}, Exception("db down"))
        self.documents.append(row)
        return datetime(2026, 3, 15, 14, 30, tzinfo=timezone.utc)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        db_check_on_startup=False,
        s3_bucket_documents=TEST_BUCKET,
        aws_region="us-east-1",
        log_level="INFO",
    )


@pytest.fixture
def repo() -> FakeRepository:
    return FakeRepository()


class NoAwsClient:
    """S3 client stand-in for tests that never touch documents."""

    def __getattr__(self, name: str):
        raise AssertionError(f"unexpected AWS call: {name}")


@pytest.fixture
def client(settings: Settings, repo: FakeRepository) -> TestClient:
    app = create_app(settings, repository=repo, s3_client=NoAwsClient())
    with TestClient(app) as test_client:
        yield test_client
