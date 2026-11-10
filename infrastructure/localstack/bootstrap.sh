#!/usr/bin/env bash
# Creates the M5 SNS topic + SQS queues/subscriptions against LocalStack.
# Safe to re-run (create calls are idempotent on LocalStack/AWS for identical names).
# Env: AWS_ENDPOINT_URL (default http://localhost:4566), AWS_REGION (default us-east-1)
set -euo pipefail

ENDPOINT="${AWS_ENDPOINT_URL:-http://localhost:4566}"
REGION="${AWS_REGION:-us-east-1}"
AWS="aws --endpoint-url=$ENDPOINT --region=$REGION"

export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"

echo "Waiting for LocalStack at $ENDPOINT ..."
for i in $(seq 1 30); do
  if $AWS sns list-topics >/dev/null 2>&1; then break; fi
  sleep 2
done

echo "Creating S3 bucket capstone-mortgage-docs-dev"
$AWS s3api create-bucket --bucket capstone-mortgage-docs-dev --region "$REGION" >/dev/null 2>&1 || true

echo "Creating S3 bucket capstone-mortgage-analytics-dev (raw/curated data lake zones, M8)"
$AWS s3api create-bucket --bucket capstone-mortgage-analytics-dev --region "$REGION" >/dev/null 2>&1 || true

echo "Hardening both buckets: block public access + default encryption (M8 task 8.2)"
for BUCKET in capstone-mortgage-docs-dev capstone-mortgage-analytics-dev; do
  $AWS s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true >/dev/null 2>&1 || true
  $AWS s3api put-bucket-encryption --bucket "$BUCKET" --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}' >/dev/null 2>&1 || true
done

echo "Tagging buckets (Project=mortgage-intelligence, Environment=dev)"
for BUCKET in capstone-mortgage-docs-dev capstone-mortgage-analytics-dev; do
  $AWS s3api put-bucket-tagging --bucket "$BUCKET" --tagging \
    'TagSet=[{Key=Project,Value=mortgage-intelligence},{Key=Environment,Value=dev}]' >/dev/null 2>&1 || true
done

echo "Creating DynamoDB table MortgageLookup-dev (M8 task 8.4)"
$AWS dynamodb create-table --table-name MortgageLookup-dev \
  --attribute-definitions AttributeName=mortgageExternalId,AttributeType=S \
  --key-schema AttributeName=mortgageExternalId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST >/dev/null 2>&1 || true

echo "Creating DynamoDB table DocumentMetadata-dev (M8 task 8.3)"
$AWS dynamodb create-table --table-name DocumentMetadata-dev \
  --attribute-definitions AttributeName=documentId,AttributeType=S \
  --key-schema AttributeName=documentId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST >/dev/null 2>&1 || true

echo "Creating SNS topic capstone-mortgage-lifecycle-dev"
TOPIC_ARN=$($AWS sns create-topic --name capstone-mortgage-lifecycle-dev --output text --query 'TopicArn')
echo "  $TOPIC_ARN"

echo "Creating DLQ capstone-mortgage-servicing-dlq-dev"
DLQ_URL=$($AWS sqs create-queue --queue-name capstone-mortgage-servicing-dlq-dev --output text --query 'QueueUrl')
DLQ_ARN=$($AWS sqs get-queue-attributes --queue-url "$DLQ_URL" --attribute-names QueueArn --output text --query 'Attributes.QueueArn')
echo "  $DLQ_URL ($DLQ_ARN)"

echo "Creating queue capstone-mortgage-servicing-dev (redrive to DLQ after 3 receives)"
REDRIVE_POLICY="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"3\"}"
SERVICING_URL=$($AWS sqs create-queue --queue-name capstone-mortgage-servicing-dev \
  --attributes "{\"VisibilityTimeout\":\"30\",\"RedrivePolicy\":\"$(echo "$REDRIVE_POLICY" | sed 's/"/\\"/g')\"}" \
  --output text --query 'QueueUrl')
SERVICING_ARN=$($AWS sqs get-queue-attributes --queue-url "$SERVICING_URL" --attribute-names QueueArn --output text --query 'Attributes.QueueArn')
echo "  $SERVICING_URL ($SERVICING_ARN)"

echo "Creating queue capstone-mortgage-analytics-dev (reserved, no consumer yet)"
ANALYTICS_URL=$($AWS sqs create-queue --queue-name capstone-mortgage-analytics-dev --output text --query 'QueueUrl')
ANALYTICS_ARN=$($AWS sqs get-queue-attributes --queue-url "$ANALYTICS_URL" --attribute-names QueueArn --output text --query 'Attributes.QueueArn')
echo "  $ANALYTICS_URL ($ANALYTICS_ARN)"

echo "Subscribing queues to the topic (RawMessageDelivery=true)"
SERVICING_SUB_ARN=$($AWS sns subscribe --topic-arn "$TOPIC_ARN" --protocol sqs --notification-endpoint "$SERVICING_ARN" --output text --query 'SubscriptionArn')
$AWS sns set-subscription-attributes --subscription-arn "$SERVICING_SUB_ARN" --attribute-name RawMessageDelivery --attribute-value true

ANALYTICS_SUB_ARN=$($AWS sns subscribe --topic-arn "$TOPIC_ARN" --protocol sqs --notification-endpoint "$ANALYTICS_ARN" --output text --query 'SubscriptionArn')
$AWS sns set-subscription-attributes --subscription-arn "$ANALYTICS_SUB_ARN" --attribute-name RawMessageDelivery --attribute-value true

echo "Done. Export these for the Java services:"
echo "  SNS_TOPIC_MORTGAGE_EVENTS=$TOPIC_ARN"
echo "  SQS_QUEUE_SERVICING_EVENTS=$SERVICING_URL"
echo "  SQS_QUEUE_SERVICING_DLQ=$DLQ_URL"
