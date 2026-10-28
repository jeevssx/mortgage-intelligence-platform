# M9 task 9.2 — formalizes the S3 buckets and DynamoDB tables that
# infrastructure/localstack/bootstrap.sh creates by hand (M5/M8) as reproducible IaC.

variable "environment" {
  type = string
}

resource "aws_s3_bucket" "documents" {
  bucket = "capstone-mortgage-docs-${var.environment}"
}

resource "aws_s3_bucket" "analytics" {
  bucket = "capstone-mortgage-analytics-${var.environment}"
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "analytics" {
  bucket                  = aws_s3_bucket.analytics.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "analytics" {
  bucket = aws_s3_bucket.analytics.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_dynamodb_table" "mortgage_lookup" {
  name         = "MortgageLookup-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "mortgageExternalId"

  attribute {
    name = "mortgageExternalId"
    type = "S"
  }
}

resource "aws_dynamodb_table" "document_metadata" {
  name         = "DocumentMetadata-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "documentId"

  attribute {
    name = "documentId"
    type = "S"
  }
}

output "documents_bucket_name" {
  value = aws_s3_bucket.documents.bucket
}

output "analytics_bucket_name" {
  value = aws_s3_bucket.analytics.bucket
}

output "mortgage_lookup_table_name" {
  value = aws_dynamodb_table.mortgage_lookup.name
}

output "document_metadata_table_name" {
  value = aws_dynamodb_table.document_metadata.name
}
