# M9 task 9.2 — formalizes the SNS/SQS/DLQ setup infrastructure/localstack/bootstrap.sh creates
# by hand (M5) as reproducible IaC. See docs/architecture/event-catalog.md for the event flow.

variable "environment" {
  type = string
}

resource "aws_sns_topic" "lifecycle_events" {
  name = "capstone-mortgage-lifecycle-${var.environment}"
}

resource "aws_sqs_queue" "servicing_dlq" {
  name = "capstone-mortgage-servicing-dlq-${var.environment}"
}

resource "aws_sqs_queue" "servicing_events" {
  name                       = "capstone-mortgage-servicing-${var.environment}"
  visibility_timeout_seconds = 30

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.servicing_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "analytics_events" {
  name = "capstone-mortgage-analytics-${var.environment}"
}

resource "aws_sns_topic_subscription" "servicing" {
  topic_arn            = aws_sns_topic.lifecycle_events.arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.servicing_events.arn
  raw_message_delivery = true
}

resource "aws_sns_topic_subscription" "analytics" {
  topic_arn            = aws_sns_topic.lifecycle_events.arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.analytics_events.arn
  raw_message_delivery = true
}

resource "aws_sqs_queue_policy" "servicing_allow_sns" {
  queue_url = aws_sqs_queue.servicing_events.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.servicing_events.arn
      Condition = { ArnEquals = { "aws:SourceArn" = aws_sns_topic.lifecycle_events.arn } }
    }]
  })
}

resource "aws_sqs_queue_policy" "analytics_allow_sns" {
  queue_url = aws_sqs_queue.analytics_events.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.analytics_events.arn
      Condition = { ArnEquals = { "aws:SourceArn" = aws_sns_topic.lifecycle_events.arn } }
    }]
  })
}

output "topic_arn" {
  value = aws_sns_topic.lifecycle_events.arn
}

output "servicing_queue_url" {
  value = aws_sqs_queue.servicing_events.id
}

output "servicing_dlq_url" {
  value = aws_sqs_queue.servicing_dlq.id
}
