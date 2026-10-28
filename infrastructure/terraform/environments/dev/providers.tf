terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Local state for dev — this environment is meant to be applied against LocalStack for fast
  # local iteration (see README.md "Why dev uses local state"). test/prod use the S3+DynamoDB
  # remote backend documented there; this file intentionally does not declare a backend block so
  # `terraform init` here always uses local state regardless of what test/prod configure.
}

variable "use_localstack" {
  description = "Point the AWS provider at LocalStack instead of real AWS."
  type        = bool
  default     = true
}

variable "localstack_endpoint" {
  description = "LocalStack endpoint URL, used only when use_localstack = true."
  type        = string
  default     = "http://localhost:4566"
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = var.use_localstack ? "test" : null
  secret_key                  = var.use_localstack ? "test" : null
  skip_credentials_validation = var.use_localstack
  skip_metadata_api_check     = var.use_localstack
  skip_requesting_account_id  = var.use_localstack
  s3_use_path_style           = var.use_localstack

  dynamic "endpoints" {
    for_each = var.use_localstack ? [1] : []
    content {
      s3       = var.localstack_endpoint
      sns      = var.localstack_endpoint
      sqs      = var.localstack_endpoint
      dynamodb = var.localstack_endpoint
      iam      = var.localstack_endpoint
      ecs      = var.localstack_endpoint
      ec2      = var.localstack_endpoint
    }
  }

  default_tags {
    tags = {
      Project     = "mortgage-intelligence"
      Environment = "dev"
    }
  }
}
