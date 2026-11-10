# M9 task 9.2 — ECS Fargate placeholder (spec explicitly allows "EC2/ECS placeholder" here,
# matching the "awareness doc OK" treatment given to EMR cluster sizing elsewhere in M8/M9).
# Defines the cluster and task definitions only — no aws_ecs_service, no load balancer, no
# running task. Real container execution for this capstone happens via docker-compose
# (docker-compose.yml) against locally-built images, not ECS; this module exists so a future
# migration from docker-compose to ECS has the task definitions already modeled in Terraform.

variable "environment" {
  type = string
}

variable "execution_role_arn" {
  description = "IAM role ECS uses to pull images and write logs (not the app's own permissions)."
  type        = string
}

variable "task_role_arn" {
  description = "IAM role the running container assumes for AWS SDK calls (mortgage-api-role / mortgage-analytics-role)."
  type        = string
}

resource "aws_ecs_cluster" "main" {
  name = "capstone-mortgage-${var.environment}"
}

resource "aws_ecs_task_definition" "mortgage_service" {
  family                   = "mortgage-service-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([{
    name         = "mortgage-service"
    image        = "mortgage-service:latest" # replaced with the registry tag the CI pipeline publishes
    portMappings = [{ containerPort = 8080, protocol = "tcp" }]
  }])
}

resource "aws_ecs_task_definition" "servicing_service" {
  family                   = "servicing-service-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([{
    name         = "servicing-service"
    image        = "servicing-service:latest"
    portMappings = [{ containerPort = 8081, protocol = "tcp" }]
  }])
}

output "cluster_name" {
  value = aws_ecs_cluster.main.name
}
