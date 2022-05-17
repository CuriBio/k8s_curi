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

resource "aws_s3_bucket" "static_host" {
  bucket = var.bucket_name
  acl    = "public-read"

  versioning {
    enabled = false
  }

  website {
    index_document = "index.html"
    error_document = "404.html"
  }
}

resource "aws_s3_bucket_policy" "static_host" {  
  bucket = aws_s3_bucket.static_host.id   
  policy = <<POLICY
{    
    "Version": "2012-10-17",    
    "Statement": [        
      {            
          "Sid": "PublicReadGetObject",            
          "Effect": "Allow",            
          "Principal": "*",            
          "Action": [                
             "s3:GetObject"            
          ],            
          "Resource": [
             "arn:aws:s3:::${aws_s3_bucket.static_host.id}/*"            
          ]        
      }    
    ]
}
POLICY
}