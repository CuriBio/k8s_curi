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
  region  = var.region
}

variable "region" {
  type = string
  default = "us-east-2"
}

resource "aws_ecr_repository" "pheno_worker_ecr" {
  name                 = "pheno-worker"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

// Get date from another state file
data "terraform_remote_state" "state1" {
  backend = "s3"
  config = {
    bucket = "curi-eks-test-cluster-tf-state"
    key = "cluster/terraform.tfstate"
    region  = "us-east-2"
  }
}
