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

module "apiv1" {
  source = "./apiv1"
}

# S3 bucket
resource "aws_s3_bucket" "phenolearn" {
  bucket = "phenolearn"
}

resource "aws_s3_bucket_policy" "phenolearn" {
    bucket = aws_s3_bucket.phenolearn.id
    policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Sid       = "EnforceTls"
                Effect    = "Deny"
                Principal = "*"
                Action    = "s3:*"
                Resource = [
                    "${aws_s3_bucket.phenolearn.arn}/*",
                    "${aws_s3_bucket.phenolearn.arn}",
                ]
                Condition = {
                    Bool = {
                        "aws:SecureTransport" = "false"
                    }
                }
            },
        ]
    })
}

resource "aws_s3_bucket_server_side_encryption_configuration" "phenolearn" {
  bucket = aws_s3_bucket.phenolearn.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_acl" "phenolearn" {
  bucket = aws_s3_bucket.phenolearn.id
  acl    = "private"
}

