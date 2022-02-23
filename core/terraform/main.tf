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

# Modules
module "aurora_database" {
  source = "./aurora_rds"

  instance_class = "db.t3.medium"
  db_secret_id   = var.db_secret_id
}
