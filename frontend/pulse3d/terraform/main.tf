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
  acl = "private"
}

data "aws_iam_policy_document" "s3_policy" {
  depends_on = [
    module.pulse3d_cloudfront
  ]
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.pulse3d_static_bucket.arn}/*"]

    principals {
      type        = "AWS"
      identifiers = module.pulse3d_cloudfront.cloudfront_origin_access_identity_iam_arns
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
  comment             = "Pulse Analysis Platform"
  enabled             = true
  is_ipv6_enabled     = true
  price_class         = "PriceClass_100"
  retain_on_delete    = false
  wait_for_deployment = false

  create_monitoring_subscription = true
  default_root_object = "login.html"
  create_origin_access_identity = true
  origin_access_identities = {
    s3_bucket_oai = "Pulse access"
  }
  origin = {
      
    s3_origin ={
      domain_name = aws_s3_bucket.pulse3d_static_bucket.bucket_regional_domain_name
      s3_origin_config = {
        origin_access_identity = "s3_bucket_oai"
      }
    } 
  }

  default_cache_behavior = {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "s3_origin"
    viewer_protocol_policy = "redirect-to-https"
  }
  viewer_certificate = {
    acm_certificate_arn = data.aws_acm_certificate.curibio_issued.arn
    ssl_support_method  = "sni-only"
  }
}
