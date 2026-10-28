locals {
  environment = "prod"
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

module "compute" {
  source             = "../../modules/compute"
  environment        = local.environment
  execution_role_arn = module.security.lambda_doc_processor_role_arn
  task_role_arn      = module.security.mortgage_api_role_arn
}

output "vpc_id" {
  value = module.networking.vpc_id
}

output "sns_topic_arn" {
  value = module.messaging.topic_arn
}
