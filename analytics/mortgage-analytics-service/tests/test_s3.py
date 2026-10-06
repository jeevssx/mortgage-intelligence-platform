"""Document upload against a moto-mocked S3 (and SNS) — no real AWS calls."""

from __future__ import annotations

import base64
import json
import os

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from src.api.main import create_app
from src.config import Settings
from src.services.document_service import sanitize_file_name
from src.utils.errors import ValidationError
from tests.conftest import TEST_BUCKET, FakeRepository

PDF = b"%PDF-1.4 synthetic test document"


@pytest.fixture(autouse=True)
def fake_aws_credentials(monkeypatch):
    for key, value in {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": "us-east-1",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("AWS_PROFILE", raising=False)


@pytest.fixture
def aws():
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=TEST_BUCKET)
        yield s3


def make_client(settings: Settings, repo: FakeRepository, s3, sns=None) -> TestClient:
    return TestClient(create_app(settings, repository=repo, s3_client=s3, sns_client=sns))


def upload_multipart(client: TestClient, mortgage="MTG-1001", doc_type="INCOME_VERIFICATION",
                     name="paystub-redacted.pdf", content=PDF, correlation_id="demo-m3-002"):
    return client.post(
        "/api/v1/documents/upload",
        data={"mortgageExternalId": mortgage, "documentType": doc_type},
        files={"file": (name, content, "application/pdf")},
        headers={"X-Correlation-Id": correlation_id},
    )


def test_multipart_upload_stores_object_and_row(settings, repo, aws):
    with make_client(settings, repo, aws) as client:
        response = upload_multipart(client)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["correlationId"] == "demo-m3-002"
    assert body["s3Key"] == f"mortgages/MTG-1001/{body['documentId']}-paystub-redacted.pdf"
    assert body["sizeBytes"] == len(PDF)
    assert body["uploadedAt"] == "2026-03-15T14:30:00Z"

    obj = aws.get_object(Bucket=TEST_BUCKET, Key=body["s3Key"])
    assert obj["Body"].read() == PDF
    assert obj["ServerSideEncryption"] == "AES256"
    assert obj["Metadata"]["correlation-id"] == "demo-m3-002"

    assert len(repo.documents) == 1
    row = repo.documents[0]
    assert row["s3_key"] == body["s3Key"]
    assert row["document_type"] == "INCOME_VERIFICATION"
    assert str(row["document_id"]) == body["documentId"]


def test_json_base64_upload(settings, repo, aws):
    with make_client(settings, repo, aws) as client:
        response = client.post(
            "/api/v1/documents/upload",
            json={
                "mortgageExternalId": "mtg-1002",
                "documentType": "hardship_letter",
                "fileName": "hardship-letter.pdf",
                "contentBase64": base64.b64encode(PDF).decode(),
            },
        )
    assert response.status_code == 201, response.text
    assert response.json()["s3Key"].startswith("mortgages/MTG-1002/")
    assert response.json()["documentType"] == "HARDSHIP_LETTER"


def test_unknown_mortgage_is_404_and_nothing_stored(settings, repo, aws):
    with make_client(settings, repo, aws) as client:
        response = upload_multipart(client, mortgage="MTG-9999")
    assert response.status_code == 404
    assert response.json()["code"] == "MORTGAGE_NOT_FOUND"
    assert aws.list_objects_v2(Bucket=TEST_BUCKET).get("KeyCount") == 0
    assert repo.documents == []


def test_s3_failure_returns_502_and_no_row(settings, repo, aws):
    broken = Settings(**{**settings.__dict__, "s3_bucket_documents": "bucket-that-does-not-exist"})
    with make_client(broken, repo, aws) as client:
        response = upload_multipart(client)
    assert response.status_code == 502
    body = response.json()
    assert body["code"] == "S3_UPLOAD_FAILED"
    assert body["correlationId"] == "demo-m3-002"
    assert repo.documents == []


def test_db_failure_rolls_back_s3_object(settings, repo, aws):
    repo.fail_insert = True
    with make_client(settings, repo, aws) as client:
        response = upload_multipart(client)
    assert response.status_code == 500
    assert response.json()["code"] == "DOCUMENT_METADATA_FAILED"
    assert aws.list_objects_v2(Bucket=TEST_BUCKET).get("KeyCount") == 0


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"doc_type": "SELFIE"}, "documentType"),
        ({"name": "malware.exe"}, "not allowed"),
        ({"content": b""}, "empty"),
        ({"mortgage": "1001"}, "mortgageExternalId"),
    ],
)
def test_upload_validation_errors(settings, repo, aws, kwargs, message):
    with make_client(settings, repo, aws) as client:
        response = upload_multipart(client, **kwargs)
    assert response.status_code == 400
    assert message in response.json()["message"]


def test_upload_too_large(settings, repo, aws):
    small = Settings(**{**settings.__dict__, "max_upload_bytes": 10})
    with make_client(small, repo, aws) as client:
        response = upload_multipart(client)
    assert response.status_code == 400
    assert "exceeds" in response.json()["message"]


def test_bad_base64_and_bad_content_type(settings, repo, aws):
    with make_client(settings, repo, aws) as client:
        bad_b64 = client.post(
            "/api/v1/documents/upload",
            json={"mortgageExternalId": "MTG-1001", "documentType": "OTHER", "fileName": "a.pdf", "contentBase64": "!!"},
        )
        missing_field = client.post("/api/v1/documents/upload", json={"mortgageExternalId": "MTG-1001"})
        text_body = client.post("/api/v1/documents/upload", content=b"x", headers={"Content-Type": "text/plain"})
        no_file = client.post("/api/v1/documents/upload", data={"mortgageExternalId": "MTG-1001"}, files={"x": ("a", b"b")})
    assert [r.status_code for r in (bad_b64, missing_field, text_body, no_file)] == [400, 400, 400, 400]


def test_sanitize_file_name():
    assert sanitize_file_name(r"C:\Users\me\pay stub (1).PDF") == "pay_stub__1_.PDF"
    assert sanitize_file_name("../../etc/passwd.pdf") == "passwd.pdf"
    with pytest.raises(ValidationError):
        sanitize_file_name("noextension")
    with pytest.raises(ValidationError):
        sanitize_file_name("")


def test_document_uploaded_event_published_to_sns(settings, repo, aws):
    sns = boto3.client("sns", region_name="us-east-1")
    sqs = boto3.client("sqs", region_name="us-east-1")
    topic_arn = sns.create_topic(Name="capstone-mortgage-lifecycle-test")["TopicArn"]
    queue_url = sqs.create_queue(QueueName="events")["QueueUrl"]
    queue_arn = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    sns.subscribe(TopicArn=topic_arn, Protocol="sqs", Endpoint=queue_arn)

    with_sns = Settings(**{**settings.__dict__, "sns_topic_mortgage_events": topic_arn})
    with make_client(with_sns, repo, aws, sns) as client:
        body = upload_multipart(client, correlation_id="demo-m3-003").json()

    messages = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)["Messages"]
    event = json.loads(json.loads(messages[0]["Body"])["Message"])
    assert event["eventType"] == "DocumentUploaded"
    assert event["schemaVersion"] == "1.0"
    assert event["correlationId"] == "demo-m3-003"
    assert event["payload"] == {
        "documentId": body["documentId"],
        "mortgageExternalId": "MTG-1001",
        "documentType": "INCOME_VERIFICATION",
        "s3Key": body["s3Key"],
    }


def test_sns_failure_does_not_fail_upload(settings, repo, aws):
    sns = boto3.client("sns", region_name="us-east-1")
    missing_topic = "arn:aws:sns:us-east-1:123456789012:does-not-exist"
    with_sns = Settings(**{**settings.__dict__, "sns_topic_mortgage_events": missing_topic})
    with make_client(with_sns, repo, aws, sns) as client:
        response = upload_multipart(client)
    assert response.status_code == 201
    assert len(repo.documents) == 1


def test_real_client_factory_uses_retries_and_timeouts(settings):
    from src.services.aws_clients import create_s3_client, create_sns_client

    s3 = create_s3_client(settings)
    # botocore stores retries={"max_attempts": 3} as 1 initial call + 3 retries
    assert s3.meta.config.retries == {"mode": "standard", "total_max_attempts": 4}
    assert s3.meta.config.read_timeout == 10
    assert s3.meta.config.connect_timeout == 5
    assert create_sns_client(settings) is None
    assert os.environ.get("AWS_PROFILE") is None
