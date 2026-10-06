"""Application exceptions. Each maps to an HTTP status and an error code in the standard envelope."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, *, code: str | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details


class ValidationError(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class UpstreamServiceError(AppError):
    """A dependency (S3, SNS) failed after retries."""

    status_code = 502
    code = "UPSTREAM_SERVICE_ERROR"


class DataIntegrityError(AppError):
    """Data read from our own database violated normalization rules: a server-side problem."""

    status_code = 500
    code = "DATA_INTEGRITY_ERROR"
