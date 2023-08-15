terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.7.0"
    }

    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "2.21.1"
    }
  }

  required_version = "1.5.2"

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
}
