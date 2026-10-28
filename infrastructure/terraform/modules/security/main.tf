# M9 task 9.2 — wraps the M8 IAM policy JSON (infrastructure/aws/iam/) as Terraform resources,
# so the roles created by hand in M8 become reproducible. Policy *content* is unchanged — these
# resources just read the same JSON files rather than re-defining the policies inline, so the
# two never drift apart.

variable "environment" {
  type = string
}

variable "iam_dir" {
  description = "Path to infrastructure/aws/iam/ (policy JSON source of truth)."
  type        = string
}

resource "aws_iam_role" "mortgage_analytics" {
  name               = "mortgage-analytics-role-${var.environment}"
  assume_role_policy = file("${var.iam_dir}/ecs-task-trust-policy.json")
}

resource "aws_iam_role_policy" "mortgage_analytics" {
  name   = "mortgage-analytics-policy"
  role   = aws_iam_role.mortgage_analytics.id
  policy = file("${var.iam_dir}/mortgage-analytics-role-policy.json")
}

resource "aws_iam_role" "mortgage_api" {
  name               = "mortgage-api-role-${var.environment}"
  assume_role_policy = file("${var.iam_dir}/ecs-task-trust-policy.json")
}

resource "aws_iam_role_policy" "mortgage_api" {
  name   = "mortgage-api-policy"
  role   = aws_iam_role.mortgage_api.id
  policy = file("${var.iam_dir}/mortgage-api-role-policy.json")
}

resource "aws_iam_role" "lambda_doc_processor" {
  name               = "capstone-lambda-doc-processor-role-${var.environment}"
  assume_role_policy = file("${var.iam_dir}/lambda-doc-processor-trust-policy.json")
}

resource "aws_iam_role_policy" "lambda_doc_processor" {
  name   = "doc-processor-policy"
  role   = aws_iam_role.lambda_doc_processor.id
  policy = file("${var.iam_dir}/lambda-doc-processor-role-policy.json")
}

output "mortgage_analytics_role_arn" {
  value = aws_iam_role.mortgage_analytics.arn
}

output "mortgage_api_role_arn" {
  value = aws_iam_role.mortgage_api.arn
}

output "lambda_doc_processor_role_arn" {
  value = aws_iam_role.lambda_doc_processor.arn
}
