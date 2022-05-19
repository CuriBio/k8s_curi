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
provider "aws" {
  alias = "virginia"
  region = "us-east-1"
}

resource "aws_s3_bucket" "pulse3d_static_bucket" {
  bucket = "dashboard.${var.domain_name}"
}
resource "aws_s3_bucket_server_side_encryption_configuration" "pulse3d_static_bucket" {
  bucket = aws_s3_bucket.pulse3d_static_bucket.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_acl" "pulse3d_static_bucket" {
  bucket = aws_s3_bucket.pulse3d_static_bucket.id
  acl = "public-read"
}

resource "aws_s3_bucket_website_configuration" "pulse3d_static_bucket" {
  bucket = aws_s3_bucket.pulse3d_static_bucket.id

  index_document {
    suffix = "login.html"
  }

  error_document {
    key = "login.html"
  }
}


data "aws_iam_policy_document" "s3_policy" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.pulse3d_static_bucket.arn}/*"]

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
  }
}

resource "aws_s3_bucket_policy" "pulse3d_bucket_policy" {
  bucket = aws_s3_bucket.pulse3d_static_bucket.id
  policy = data.aws_iam_policy_document.s3_policy.json
}


data "aws_acm_certificate" "curibio_issued" {
  domain   = "*.${var.domain_name}"
  types       = ["AMAZON_ISSUED"]
  provider = aws.virginia
}

module "pulse3d_cloudfront" {
  source = "terraform-aws-modules/cloudfront/aws"
  depends_on = [
    data.aws_acm_certificate.curibio_issued
  ]
  aliases = [aws_s3_bucket.pulse3d_static_bucket.bucket]
  comment             = "Pulse3D"
  enabled             = true
  is_ipv6_enabled     = true
  price_class         = "PriceClass_All"
  retain_on_delete    = false
  wait_for_deployment = false

  create_monitoring_subscription = true
  create_origin_access_identity = false

  origin = {
    s3_origin ={
      domain_name = aws_s3_bucket_website_configuration.pulse3d_static_bucket.website_endpoint

      custom_origin_config = {
          http_port              = 80
          https_port             = 443
          origin_protocol_policy = "match-viewer"
          origin_ssl_protocols   = ["TLSv1", "TLSv1.1", "TLSv1.2"]
      }
    } 
  }

  default_cache_behavior = {
    target_origin_id = "s3_origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    query_string           = true
  }


  viewer_certificate = {
    acm_certificate_arn = data.aws_acm_certificate.curibio_issued.arn
    ssl_support_method  = "sni-only"
  }


}
