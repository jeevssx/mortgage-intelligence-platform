"""Document upload workflow: validate → S3 put → `document` row → optional SNS event."""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.exc import SQLAlchemyError

from src.analytics.normalization import MORTGAGE_ID_RE
from src.config import Settings
from src.repositories.mortgage_repository import MortgageDataSource
from src.utils.errors import AppError, NotFoundError, UpstreamServiceError, ValidationError
from src.utils.logging_config import get_correlation_id

logger = logging.getLogger(__name__)

DOCUMENT_TYPES = frozenset(
    {
        "INCOME_VERIFICATION",
        "APPRAISAL",
        "CLOSING_DISCLOSURE",
        "HARDSHIP_LETTER",
        "LIEN_RELEASE",
        "IDENTITY_VERIFICATION",
        "OTHER",
    }
)
ALLOWED_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"})
_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


@dataclass(frozen=True)
class UploadResult:
    document_id: uuid.UUID
    mortgage_external_id: str
    document_type: str
    file_name: str
    s3_key: str
    size_bytes: int
    uploaded_at: datetime


def sanitize_file_name(file_name: str) -> str:
    """Strip any path, replace unsafe characters, and enforce an allowed extension."""
    base = re.split(r"[\\/]", file_name or "")[-1].strip()
    base = _UNSAFE_CHARS.sub("_", base).lstrip(".")
    if not base:
        raise ValidationError("fileName is required")
    ext = ("." + base.rsplit(".", 1)[-1].lower()) if "." in base else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"File type {ext or '(none)'} is not allowed; use one of {sorted(ALLOWED_EXTENSIONS)}")
    return base[-200:]


class DocumentService:
    def __init__(
        self,
        repository: MortgageDataSource,
        s3_client: Any,
        settings: Settings,
        sns_client: Any | None = None,
    ) -> None:
        self._repo = repository
        self._s3 = s3_client
        self._sns = sns_client
        self._settings = settings

    def upload(
        self,
        *,
        mortgage_external_id: str,
        document_type: str,
        file_name: str,
        content: bytes,
        content_type: str | None = None,
    ) -> UploadResult:
        mortgage_external_id = (mortgage_external_id or "").strip().upper()
        document_type = (document_type or "").strip().upper()
        if not MORTGAGE_ID_RE.match(mortgage_external_id):
            raise ValidationError(f"Invalid mortgageExternalId {mortgage_external_id!r}")
        if document_type not in DOCUMENT_TYPES:
            raise ValidationError(f"documentType must be one of {sorted(DOCUMENT_TYPES)}")
        safe_name = sanitize_file_name(file_name)
        if not content:
            raise ValidationError("File is empty")
        if len(content) > self._settings.max_upload_bytes:
            raise ValidationError(f"File exceeds {self._settings.max_upload_bytes} bytes")

        mortgage_id = self._repo.find_mortgage_id(mortgage_external_id)
        if mortgage_id is None:
            raise NotFoundError(f"Mortgage {mortgage_external_id} was not found", code="MORTGAGE_NOT_FOUND")

        document_id = uuid.uuid4()
        s3_key = f"mortgages/{mortgage_external_id}/{document_id}-{safe_name}"
        log_ctx = {"mortgageId": mortgage_external_id, "documentId": str(document_id), "s3Key": s3_key}

        self._put_object(s3_key, content, content_type, mortgage_external_id, log_ctx)

        try:
            uploaded_at = self._repo.insert_document(
                document_id=document_id,
                mortgage_id=mortgage_id,
                document_type=document_type,
                s3_key=s3_key,
                file_name=safe_name,
            )
        except SQLAlchemyError as exc:
            self._delete_object_best_effort(s3_key, log_ctx)
            raise AppError("Failed to record document metadata", code="DOCUMENT_METADATA_FAILED") from exc

        logger.info("Document uploaded", extra={**log_ctx, "sizeBytes": len(content)})
        result = UploadResult(
            document_id=document_id,
            mortgage_external_id=mortgage_external_id,
            document_type=document_type,
            file_name=safe_name,
            s3_key=s3_key,
            size_bytes=len(content),
            uploaded_at=uploaded_at,
        )
        self._publish_event(result)
        return result

    def _put_object(
        self, key: str, content: bytes, content_type: str | None, mortgage_external_id: str, log_ctx: dict
    ) -> None:
        try:
            self._s3.put_object(
                Bucket=self._settings.s3_bucket_documents,
                Key=key,
                Body=content,
                ContentType=content_type or "application/octet-stream",
                ServerSideEncryption="AES256",
                Metadata={
                    "mortgage-external-id": mortgage_external_id,
                    "correlation-id": get_correlation_id() or "",
                },
            )
        except (ClientError, BotoCoreError) as exc:
            logger.error("S3 upload failed", extra={**log_ctx, "error": type(exc).__name__})
            raise UpstreamServiceError("Document storage is unavailable", code="S3_UPLOAD_FAILED") from exc

    def _delete_object_best_effort(self, key: str, log_ctx: dict) -> None:
        try:
            self._s3.delete_object(Bucket=self._settings.s3_bucket_documents, Key=key)
            logger.warning("Rolled back S3 object after metadata failure", extra=log_ctx)
        except (ClientError, BotoCoreError):
            logger.error("Could not roll back orphaned S3 object", extra=log_ctx)

    def _publish_event(self, result: UploadResult) -> None:
        """Publish DocumentUploaded (envelope per reference/payload-examples.json). Never fails the upload."""
        topic = self._settings.sns_topic_mortgage_events
        if not topic or self._sns is None:
            return
        event = {
            "eventId": str(uuid.uuid4()),
            "eventType": "DocumentUploaded",
            "schemaVersion": "1.0",
            "occurredAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "correlationId": get_correlation_id(),
            "payload": {
                "documentId": str(result.document_id),
                "mortgageExternalId": result.mortgage_external_id,
                "documentType": result.document_type,
                "s3Key": result.s3_key,
            },
        }
        try:
            self._sns.publish(
                TopicArn=topic,
                Message=json.dumps(event),
                MessageAttributes={"eventType": {"DataType": "String", "StringValue": "DocumentUploaded"}},
            )
            logger.info("Published DocumentUploaded", extra={"eventId": event["eventId"], "mortgageId": result.mortgage_external_id})
        except (ClientError, BotoCoreError) as exc:
            logger.warning("DocumentUploaded publish failed", extra={"error": type(exc).__name__, "mortgageId": result.mortgage_external_id})
