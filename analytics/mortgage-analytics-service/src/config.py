"""Service configuration loaded from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


def _bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    service_name: str = "mortgage-analytics-service"
    log_level: str = "INFO"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "mortgage_intel"
    postgres_user: str = "mortgage_app"
    postgres_password: str = ""
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_connect_timeout_seconds: int = 5
    db_check_on_startup: bool = True

    aws_region: str = "us-east-1"
    aws_profile: str | None = None
    s3_bucket_documents: str = "capstone-mortgage-docs-dev"
    aws_endpoint_url: str | None = None
    sns_topic_mortgage_events: str | None = None
    aws_connect_timeout_seconds: int = 5
    aws_read_timeout_seconds: int = 10
    aws_max_attempts: int = 3

    max_upload_bytes: int = 10 * 1024 * 1024

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}@{self.postgres_host}:"
            f"{self.postgres_port}/{self.postgres_db}"
        )

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        env = os.environ.get
        return cls(
            service_name=env("SERVICE_NAME", cls.service_name),
            log_level=env("LOG_LEVEL", cls.log_level).upper(),
            postgres_host=env("POSTGRES_HOST", cls.postgres_host),
            postgres_port=int(env("POSTGRES_PORT", str(cls.postgres_port))),
            postgres_db=env("POSTGRES_DB", cls.postgres_db),
            postgres_user=env("POSTGRES_USER", cls.postgres_user),
            postgres_password=env("POSTGRES_PASSWORD", ""),
            db_pool_size=int(env("DB_POOL_SIZE", str(cls.db_pool_size))),
            db_max_overflow=int(env("DB_MAX_OVERFLOW", str(cls.db_max_overflow))),
            db_connect_timeout_seconds=int(
                env("DB_CONNECT_TIMEOUT_SECONDS", str(cls.db_connect_timeout_seconds))
            ),
            db_check_on_startup=_bool(env("DB_CHECK_ON_STARTUP"), cls.db_check_on_startup),
            aws_region=env("AWS_REGION", cls.aws_region),
            aws_profile=env("AWS_PROFILE") or None,
            s3_bucket_documents=env("S3_BUCKET_DOCUMENTS", cls.s3_bucket_documents),
            aws_endpoint_url=env("AWS_ENDPOINT_URL") or None,
            sns_topic_mortgage_events=env("SNS_TOPIC_MORTGAGE_EVENTS") or None,
            max_upload_bytes=int(env("MAX_UPLOAD_BYTES", str(cls.max_upload_bytes))),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
