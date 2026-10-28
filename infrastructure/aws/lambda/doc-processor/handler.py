"""capstone-doc-processor-dev — M8 task 8.3.

Triggered by s3:ObjectCreated on capstone-mortgage-docs-dev. Validates the uploaded file's type
and writes a metadata row to DynamoDB (DocumentMetadata-dev) — the asynchronous counterpart to
the synchronous document-metadata write mortgage-analytics-service already does in its own
`document` PostgreSQL table at upload time (M3). This Lambda does not duplicate that write; it
demonstrates the event-driven processing pattern against the same upload event, writing to a
separate fast-lookup table.

Key format (must match mortgage-analytics-service's DocumentService):
  mortgages/{mortgageExternalId}/{documentId}-{fileName}
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from urllib.parse import unquote_plus

import boto3

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
TABLE_NAME = os.environ.get("DYNAMODB_TABLE_DOCUMENT_METADATA", "DocumentMetadata-dev")
_UUID_PREFIX = re.compile(r"^([0-9a-fA-F-]{36})-(.+)$")

_dynamodb = None


def _endpoint_url() -> str | None:
    # LocalStack injects LOCALSTACK_HOSTNAME into the Lambda execution container so it can call
    # back to itself regardless of the host's Docker network topology — more reliable than a
    # fixed AWS_ENDPOINT_URL value, which only resolves if this function's container happens to
    # share a network with a container actually named that. Real AWS sets neither, so this is a
    # no-op there (boto3 uses its default endpoint resolution).
    if "LOCALSTACK_HOSTNAME" in os.environ:
        return f"http://{os.environ['LOCALSTACK_HOSTNAME']}:4566"
    return os.environ.get("AWS_ENDPOINT_URL") or None


def _table():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb", endpoint_url=_endpoint_url())
    return _dynamodb.Table(TABLE_NAME)


def handler(event: dict, _context) -> dict:
    results = []
    for record in event.get("Records", []):
        results.append(_process_record(record))
    return {"processed": len(results), "results": results}


def _process_record(record: dict) -> dict:
    bucket = record["s3"]["bucket"]["name"]
    key = unquote_plus(record["s3"]["object"]["key"])
    size = record["s3"]["object"].get("size", 0)

    parts = key.split("/")
    mortgage_external_id = parts[1] if len(parts) >= 2 and parts[0] == "mortgages" else None
    file_name_part = parts[-1] if parts else key

    match = _UUID_PREFIX.match(file_name_part)
    if match:
        document_id, file_name = match.group(1), match.group(2)
    else:
        document_id, file_name = str(uuid.uuid4()), file_name_part

    _, ext = os.path.splitext(file_name.lower())
    valid = ext in ALLOWED_EXTENSIONS

    log_payload = {
        "bucket": bucket,
        "s3Key": key,
        "documentId": document_id,
        "mortgageExternalId": mortgage_external_id,
        "fileName": file_name,
        "sizeBytes": size,
        "validationStatus": "VALID" if valid else "REJECTED_FILE_TYPE",
    }
    logger.info(json.dumps(log_payload))

    _table().put_item(
        Item={
            "documentId": document_id,
            "mortgageExternalId": mortgage_external_id or "UNKNOWN",
            "s3Key": key,
            "fileName": file_name,
            "sizeBytes": size,
            "validationStatus": log_payload["validationStatus"],
            "processedAt": int(time.time()),
        }
    )

    if not valid:
        logger.warning(json.dumps({**log_payload, "message": "File type not in allow-list"}))

    return log_payload
