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

  required_version = "1.1.0"

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

resource "aws_ecr_repository" "test2_service_ecr" {
  name                 = "test2"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}
