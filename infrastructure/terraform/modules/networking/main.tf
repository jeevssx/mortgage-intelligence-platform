# M9 task 9.2 — VPC/security groups baseline (Session 32).
# Mirrors the trust boundaries already documented in docs/architecture/trust-boundaries.md:
# app tier can reach the data tier and the internet (for AWS SDK calls); nothing inbound from
# the internet reaches the data tier directly.

variable "environment" {
  type = string
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "app_subnet_cidr" {
  type    = string
  default = "10.0.1.0/24"
}

variable "data_subnet_cidr" {
  type    = string
  default = "10.0.2.0/24"
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "capstone-mortgage-vpc-${var.environment}"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "capstone-mortgage-igw-${var.environment}"
  }
}

resource "aws_subnet" "app" {
  vpc_id     = aws_vpc.main.id
  cidr_block = var.app_subnet_cidr

  tags = {
    Name = "capstone-mortgage-app-subnet-${var.environment}"
    Tier = "app"
  }
}

# No route to the internet gateway for the data subnet — it has no direct internet path in or
# out, matching the "data tier has no internet route" trust boundary.
resource "aws_subnet" "data" {
  vpc_id     = aws_vpc.main.id
  cidr_block = var.data_subnet_cidr

  tags = {
    Name = "capstone-mortgage-data-subnet-${var.environment}"
    Tier = "data"
  }
}

resource "aws_route_table" "app" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "capstone-mortgage-app-rt-${var.environment}"
  }
}

resource "aws_route_table_association" "app" {
  subnet_id      = aws_subnet.app.id
  route_table_id = aws_route_table.app.id
}

resource "aws_security_group" "app" {
  name        = "capstone-mortgage-app-sg-${var.environment}"
  description = "Java/Python application services — inbound only on their own ports"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "mortgage-service, servicing-service, analytics-service, ai-assistant"
    from_port   = 8000
    to_port     = 8081
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "Outbound to AWS APIs and the data tier"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "capstone-mortgage-app-sg-${var.environment}"
  }
}

resource "aws_security_group" "data" {
  name        = "capstone-mortgage-data-sg-${var.environment}"
  description = "PostgreSQL — inbound only from the app tier security group, never from 0.0.0.0/0"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from the app tier only"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  tags = {
    Name = "capstone-mortgage-data-sg-${var.environment}"
  }
}

output "vpc_id" {
  value = aws_vpc.main.id
}

output "app_subnet_id" {
  value = aws_subnet.app.id
}

output "data_subnet_id" {
  value = aws_subnet.data.id
}

output "app_security_group_id" {
  value = aws_security_group.app.id
}

output "data_security_group_id" {
  value = aws_security_group.data.id
}
