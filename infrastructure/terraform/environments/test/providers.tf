# test and prod target REAL AWS (no LocalStack override) — see
# infrastructure/terraform/README.md for why this environment has never been applied: no real
# AWS account is available in this build. The backend below is the exact S3+DynamoDB remote
# state example from m09-cicd-terraform-observability.md; `terraform init` for this environment
# has not been run (it would fail without those two resources existing and real credentials).

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "capstone-mortgage-tfstate-test"
    key            = "mortgage-intelligence/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "capstone-mortgage-tflock-test"
    encrypt        = true
  }
}

provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = "mortgage-intelligence"
      Environment = "test"
    }
  }
}
