"""boto3 clients with retries and timeouts. Credentials come from AWS_PROFILE / IAM role, never code."""

from __future__ import annotations

from typing import Any

import boto3
from botocore.config import Config

from src.config import Settings


def _session(settings: Settings) -> boto3.session.Session:
    if settings.aws_profile:
        return boto3.session.Session(profile_name=settings.aws_profile, region_name=settings.aws_region)
    return boto3.session.Session(region_name=settings.aws_region)


def _config(settings: Settings) -> Config:
    return Config(
        retries={"max_attempts": settings.aws_max_attempts, "mode": "standard"},
        connect_timeout=settings.aws_connect_timeout_seconds,
        read_timeout=settings.aws_read_timeout_seconds,
    )


def create_s3_client(settings: Settings) -> Any:
    return _session(settings).client("s3", config=_config(settings), endpoint_url=settings.aws_endpoint_url)


def create_sns_client(settings: Settings) -> Any | None:
    if not settings.sns_topic_mortgage_events:
        return None
    return _session(settings).client("sns", config=_config(settings), endpoint_url=settings.aws_endpoint_url)
