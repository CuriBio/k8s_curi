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

resource "aws_ecr_repository" "queue_processor_ecr" {
  name                 = "queue-processor"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "queue_processor_ecr_lifecycle_policy" {
  repository = aws_ecr_repository.queue_processor_ecr.name

  policy = <<EOF
{
    "rules": [
        {
            "rulePriority": 1,
            "description": "Keep last 3 tagged images",
            "selection": {
                "tagStatus": "tagged",
                "tagPrefixList": ["0"],
                "countType": "imageCountMoreThan",
                "countNumber": 3
            },
            "action": {
                "type": "expire"
            }
        },
        {
            "rulePriority": 2,
            "description": "Keep only 1 untagged image",
            "selection": {
                "tagStatus": "untagged",
                "countType": "imageCountMoreThan",
                "countNumber": 1
            },
            "action": {
                "type": "expire"
            }
        }
    ]
}
EOF
}
