terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.89.0, < 6.0.0"
    }

    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "2.21.1"
    }
  }

  required_version = "1.5.7"

  backend "s3" {
  }
}


# Configure the AWS Provider
provider "aws" {
  region = var.region
}

# Modules
module "aurora_database" {
  source = "./aurora_rds"

  name           = var.aurora_database_name
  environment    = var.environment
  instance_class = var.aurora_instance_class

  password_change_id = var.password_change_id

  cluster_vpc = var.cluster_vpc
}

module "alb_waf" {
  source = "./waf"
  alb_arn = var.alb_arn
  log_blocked_requests_only = false

  data_protections = [
    {
      field_type                 = "SINGLE_HEADER"
      field_keys                 = ["authorization", "proxy-authorization", "cookie", "x-api-key"]
      action                     = "HASH"
      exclude_rule_match_details = true
    },
    {
      field_type                 = "BODY"
      action                     = "SUBSTITUTION"
      exclude_rule_match_details = false
    },
    {
      field_type = "SINGLE_QUERY_ARGUMENT"
      field_keys = ["access_token", "token", "api_key"]
      action     = "SUBSTITUTION"
    },
  ]
}
