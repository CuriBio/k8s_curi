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

  backend "s3" {
  }
}

# Configure the AWS Provider
provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "us-east-2"
}

module "users" {
  source = "./users"
}


module "mantarray" {
  source       = "./mantarray"
  cluster_name = var.cluster_name
}

