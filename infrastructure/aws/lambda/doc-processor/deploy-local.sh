#!/usr/bin/env bash
# Packages and deploys capstone-doc-processor-dev to LocalStack, and wires the S3 trigger.
# Safe to re-run: update-function-code / put-bucket-notification-configuration are idempotent.
set -euo pipefail

ENDPOINT="${AWS_ENDPOINT_URL:-http://localhost:4566}"
REGION="${AWS_REGION:-us-east-1}"
AWS="aws --endpoint-url=$ENDPOINT --region=$REGION"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"

ZIP_PATH="${TMPDIR:-/tmp}/capstone-doc-processor-function.zip"
rm -f "$ZIP_PATH"
# Written to a temp dir, not next to the script, since the script's own directory may be a
# read-only mount (e.g. docker-compose's localstack-init service). Requires `zip` on PATH —
# docker-compose's localstack-init installs it; it's standard on most dev workstations.
(cd "$SCRIPT_DIR" && zip -q "$ZIP_PATH" handler.py)

echo "Creating IAM role capstone-lambda-doc-processor-role"
$AWS iam create-role --role-name capstone-lambda-doc-processor-role \
  --assume-role-policy-document "file://$SCRIPT_DIR/../../iam/lambda-doc-processor-trust-policy.json" >/dev/null 2>&1 || true
$AWS iam put-role-policy --role-name capstone-lambda-doc-processor-role \
  --policy-name doc-processor-policy \
  --policy-document "file://$SCRIPT_DIR/../../iam/lambda-doc-processor-role-policy.json" >/dev/null 2>&1 || true

echo "Creating/updating Lambda function capstone-doc-processor-dev"
if $AWS lambda get-function --function-name capstone-doc-processor-dev >/dev/null 2>&1; then
  $AWS lambda update-function-code --function-name capstone-doc-processor-dev \
    --zip-file "fileb://$ZIP_PATH" >/dev/null
else
  $AWS lambda create-function --function-name capstone-doc-processor-dev \
    --runtime python3.12 \
    --handler handler.handler \
    --role arn:aws:iam::000000000000:role/capstone-lambda-doc-processor-role \
    --zip-file "fileb://$ZIP_PATH" \
    --environment "Variables={DYNAMODB_TABLE_DOCUMENT_METADATA=DocumentMetadata-dev,AWS_ENDPOINT_URL=http://localstack:4566}" \
    --timeout 30 >/dev/null
fi

echo "Granting S3 permission to invoke the function"
$AWS lambda add-permission --function-name capstone-doc-processor-dev \
  --statement-id s3-invoke --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::capstone-mortgage-docs-dev >/dev/null 2>&1 || true

echo "Waiting for the function to become Active"
$AWS lambda wait function-active --function-name capstone-doc-processor-dev

LAMBDA_ARN=$($AWS lambda get-function --function-name capstone-doc-processor-dev --query 'Configuration.FunctionArn' --output text)

echo "Wiring S3 ObjectCreated notification (prefix: mortgages/) -> Lambda"
$AWS s3api put-bucket-notification-configuration --bucket capstone-mortgage-docs-dev \
  --notification-configuration "{\"LambdaFunctionConfigurations\":[{\"LambdaFunctionArn\":\"$LAMBDA_ARN\",\"Events\":[\"s3:ObjectCreated:*\"],\"Filter\":{\"Key\":{\"FilterRules\":[{\"Name\":\"prefix\",\"Value\":\"mortgages/\"}]}}}]}"

echo "Done. Function ARN: $LAMBDA_ARN"
