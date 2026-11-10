# Never applied — see environments/test/providers.tf and infrastructure/terraform/README.md for
# why (no real AWS account in this build). In a real pipeline, prod additionally requires a
# manual approval gate in CI before `terraform apply` runs here (docs/operations/cicd.md) — that
# gate lives in the pipeline, not in this Terraform config.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "capstone-mortgage-tfstate-prod"
    key            = "mortgage-intelligence/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "capstone-mortgage-tflock-prod"
    encrypt        = true
  }
}

provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = "mortgage-intelligence"
      Environment = "prod"
    }
  }
}
