from __future__ import annotations

import base64
import binascii
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError as PydanticValidationError

from src.api.dependencies import get_document_service
from src.models.schemas import DocumentUploadJson, DocumentUploadResponse, ErrorResponse
from src.services.document_service import DocumentService, UploadResult
from src.utils.errors import ValidationError
from src.utils.logging_config import get_correlation_id

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)


def _response(result: UploadResult) -> DocumentUploadResponse:
    return DocumentUploadResponse(
        documentId=str(result.document_id),
        mortgageExternalId=result.mortgage_external_id,
        documentType=result.document_type,
        fileName=result.file_name,
        s3Key=result.s3_key,
        sizeBytes=result.size_bytes,
        uploadedAt=result.uploaded_at.isoformat().replace("+00:00", "Z"),
        correlationId=get_correlation_id(),
    )


@router.post(
    "/upload",
    status_code=201,
    response_model=DocumentUploadResponse,
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["mortgageExternalId", "documentType", "file"],
                        "properties": {
                            "mortgageExternalId": {"type": "string", "example": "MTG-1001"},
                            "documentType": {"type": "string", "example": "INCOME_VERIFICATION"},
                            "file": {"type": "string", "format": "binary"},
                        },
                    }
                },
                "application/json": {"schema": DocumentUploadJson.model_json_schema()},
            },
            "required": True,
        }
    },
)
async def upload_document(
    request: Request,
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentUploadResponse:
    """Upload a document to S3 and record its metadata. Accepts multipart (preferred) or JSON with base64."""
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if upload is None or isinstance(upload, str):
            raise ValidationError("Multipart field 'file' is required")
        result = service.upload(
            mortgage_external_id=str(form.get("mortgageExternalId") or ""),
            document_type=str(form.get("documentType") or ""),
            file_name=upload.filename or "",
            content=await upload.read(),
            content_type=upload.content_type,
        )
    elif content_type.startswith("application/json"):
        try:
            body = DocumentUploadJson.model_validate(await request.json())
        except (PydanticValidationError, ValueError) as exc:
            raise ValidationError("Invalid JSON upload request") from exc
        try:
            content = base64.b64decode(body.contentBase64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValidationError("contentBase64 is not valid base64") from exc
        result = service.upload(
            mortgage_external_id=body.mortgageExternalId,
            document_type=body.documentType,
            file_name=body.fileName,
            content=content,
            content_type=body.contentType,
        )
    else:
        raise ValidationError("Content-Type must be multipart/form-data or application/json")
    return _response(result)
