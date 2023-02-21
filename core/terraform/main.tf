terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "4.30.0"
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

# Modules
module "aurora_database" {
  source = "./aurora_rds"

  name            = var.aurora_database_name
  environment     = var.environment
  instance_class  = var.aurora_instance_class

  password_change_id = var.password_change_id
}
