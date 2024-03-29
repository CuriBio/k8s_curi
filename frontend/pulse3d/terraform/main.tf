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
provider "aws" {
  alias  = "virginia"
  region = "us-east-1"
}

resource "aws_s3_bucket" "pulse3d_static_bucket" {
  bucket = "dashboard.${var.domain_name}"
}

resource "aws_s3_bucket_ownership_controls" "pulse3d_static_bucket" {
  bucket = aws_s3_bucket.pulse3d_static_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "pulse3d_static_bucket" {
  bucket = aws_s3_bucket.pulse3d_static_bucket.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_policy" "pulse3d_static_bucket" {
    depends_on = [
      module.pulse3d_cloudfront
    ]
    bucket = aws_s3_bucket.pulse3d_static_bucket.id
    policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Sid       = "EnforceTls"
                Effect    = "Deny"
                Principal = "*"
                Action    = "s3:*"
                Resource = [
                    "${aws_s3_bucket.pulse3d_static_bucket.arn}/*",
                    "${aws_s3_bucket.pulse3d_static_bucket.arn}",
                ]
                Condition = {
                    Bool = {
                        "aws:SecureTransport" = "false"
                    }
                }
            },
            {
                Sid       = "CloudFrontAccess"
                Effect    = "Allow"
                Principal = "*"
                Action    = "s3:GetObject"
                Resource = ["${aws_s3_bucket.pulse3d_static_bucket.arn}/*"]
                Principal = {
                  "AWS" = module.pulse3d_cloudfront.cloudfront_origin_access_identity_iam_arns
                }
            },
        ]
    })
}

data "aws_acm_certificate" "curibio_issued" {
  domain   = "*.${var.domain_name}"
  types    = ["AMAZON_ISSUED"]
  provider = aws.virginia
}

module "pulse3d_cloudfront" {
  source = "terraform-aws-modules/cloudfront/aws"
  depends_on = [
    data.aws_acm_certificate.curibio_issued
  ]

  aliases             = [aws_s3_bucket.pulse3d_static_bucket.bucket]
  comment             = "Pulse Analysis Platform"
  enabled             = true
  is_ipv6_enabled     = true
  price_class         = "PriceClass_100"
  retain_on_delete    = false
  wait_for_deployment = false

  create_monitoring_subscription = true
  default_root_object            = "login"
  create_origin_access_identity  = true
  origin_access_identities = {
    s3_bucket_oai = "Pulse access"
  }
  origin = {

    s3_origin = {
      domain_name = aws_s3_bucket.pulse3d_static_bucket.bucket_regional_domain_name
      origin_path = "/v0.7.9"
      s3_origin_config = {
        origin_access_identity = "s3_bucket_oai"
      }
    }
  }

  default_cache_behavior = {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3_origin"
    viewer_protocol_policy = "redirect-to-https"
  }
  viewer_certificate = {
    acm_certificate_arn = data.aws_acm_certificate.curibio_issued.arn
    ssl_support_method  = "sni-only"
  }
}
