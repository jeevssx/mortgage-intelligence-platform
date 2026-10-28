locals {
  environment = "dev"
  iam_dir     = "${path.module}/../../../aws/iam"
}

module "networking" {
  source      = "../../modules/networking"
  environment = local.environment
}

module "security" {
  source      = "../../modules/security"
  environment = local.environment
  iam_dir     = local.iam_dir
}

module "storage" {
  source      = "../../modules/storage"
  environment = local.environment
}

module "messaging" {
  source      = "../../modules/messaging"
  environment = local.environment
}

# ECS is a LocalStack Pro feature (Community returns 501 "pro feature" for CreateCluster /
# RegisterTaskDefinition — confirmed by actually running `terraform apply` against it). Disabled
# by default here so `terraform apply` succeeds cleanly against LocalStack Community; set true
# for real AWS or LocalStack Pro. See infrastructure/terraform/README.md.
variable "enable_compute" {
  type    = bool
  default = false
}

module "compute" {
  count              = var.enable_compute ? 1 : 0
  source             = "../../modules/compute"
  environment        = local.environment
  execution_role_arn = module.security.lambda_doc_processor_role_arn
  task_role_arn      = module.security.mortgage_api_role_arn
}

output "vpc_id" {
  value = module.networking.vpc_id
}

output "documents_bucket_name" {
  value = module.storage.documents_bucket_name
}

output "analytics_bucket_name" {
  value = module.storage.analytics_bucket_name
}

output "sns_topic_arn" {
  value = module.messaging.topic_arn
}

output "ecs_cluster_name" {
  value = var.enable_compute ? module.compute[0].cluster_name : null
}
