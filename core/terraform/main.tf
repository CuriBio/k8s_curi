terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "4.0.0"
    }

    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "2.8.0"
    }
  }

  required_version = "1.1.6"

  backend "s3" {}
}


# Configure the AWS Provider
provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "us-east-2"
}

# Modules
# module "aurora_database" {
#   source = "./aurora_rds"

#   instance_class = "db.t3.small"
#   db_creds_arn   = var.db_creds_arn
# }
