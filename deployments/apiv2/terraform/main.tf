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

module "event_broker" {
  source = "./event-broker"
}
