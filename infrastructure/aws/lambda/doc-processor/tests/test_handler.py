import os
import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.pop("AWS_ENDPOINT_URL", None)  # moto intercepts boto3 calls; no real endpoint needed

import handler  # noqa: E402


def _s3_created_event(key: str, size: int = 1234) -> dict:
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "capstone-mortgage-docs-dev"},
                    "object": {"key": key, "size": size},
                }
            }
        ]
    }


@pytest.fixture(autouse=True)
def reset_table_cache():
    handler._dynamodb = None
    yield
    handler._dynamodb = None


@mock_aws
def _make_table():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName=handler.TABLE_NAME,
        KeySchema=[{"AttributeName": "documentId", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "documentId", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )


@mock_aws
def test_valid_document_is_stored_with_parsed_metadata():
    _make_table()
    key = "mortgages/MTG-1001/550e8400-e29b-41d4-a716-446655440000-paystub.pdf"

    result = handler.handler(_s3_created_event(key), None)

    assert result["processed"] == 1
    record = result["results"][0]
    assert record["mortgageExternalId"] == "MTG-1001"
    assert record["documentId"] == "550e8400-e29b-41d4-a716-446655440000"
    assert record["fileName"] == "paystub.pdf"
    assert record["validationStatus"] == "VALID"

    table = boto3.resource("dynamodb", region_name="us-east-1").Table(handler.TABLE_NAME)
    item = table.get_item(Key={"documentId": "550e8400-e29b-41d4-a716-446655440000"})["Item"]
    assert item["mortgageExternalId"] == "MTG-1001"
    assert item["s3Key"] == key


@mock_aws
def test_disallowed_extension_is_flagged_but_still_recorded():
    _make_table()
    key = "mortgages/MTG-1002/550e8400-e29b-41d4-a716-446655440001-script.exe"

    result = handler.handler(_s3_created_event(key), None)

    record = result["results"][0]
    assert record["validationStatus"] == "REJECTED_FILE_TYPE"

    table = boto3.resource("dynamodb", region_name="us-east-1").Table(handler.TABLE_NAME)
    item = table.get_item(Key={"documentId": "550e8400-e29b-41d4-a716-446655440001"})["Item"]
    assert item["validationStatus"] == "REJECTED_FILE_TYPE"


@mock_aws
def test_key_without_uuid_prefix_still_generates_a_document_id():
    _make_table()
    key = "mortgages/MTG-1003/some-weird-name.pdf"

    result = handler.handler(_s3_created_event(key), None)

    record = result["results"][0]
    assert record["mortgageExternalId"] == "MTG-1003"
    assert len(record["documentId"]) == 36  # generated UUID4


@mock_aws
def test_key_outside_mortgages_prefix_has_unknown_mortgage_id():
    _make_table()
    key = "other-prefix/file.pdf"

    result = handler.handler(_s3_created_event(key), None)

    assert result["results"][0]["mortgageExternalId"] is None

    table = boto3.resource("dynamodb", region_name="us-east-1").Table(handler.TABLE_NAME)
    scan = table.scan()["Items"]
    assert scan[0]["mortgageExternalId"] == "UNKNOWN"


@mock_aws
def test_multiple_records_in_one_event_are_all_processed():
    _make_table()
    event = {
        "Records": [
            _s3_created_event("mortgages/MTG-1001/" + "a" * 36 + "-one.pdf")["Records"][0],
            _s3_created_event("mortgages/MTG-1002/" + "b" * 36 + "-two.pdf")["Records"][0],
        ]
    }

    result = handler.handler(event, None)

    assert result["processed"] == 2
