resource "aws_ecr_repository" "pulse3d_ecr_repo" {
  name                 = "pulse3d_api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}


resource "aws_s3_bucket" "pulse3d_uploads_bucket" {
  bucket = "${var.cluster_name}-pulse3d-uploads"
}

resource "aws_s3_bucket_policy" "pulse3d_uploads_bucket" {
    bucket = aws_s3_bucket.pulse3d_uploads_bucket.id
    policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Sid       = "EnforceTls"
                Effect    = "Deny"
                Principal = "*"
                Action    = "s3:*"
                Resource = [
                    "${aws_s3_bucket.pulse3d_uploads_bucket.arn}/*",
                    "${aws_s3_bucket.pulse3d_uploads_bucket.arn}",
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

resource "aws_s3_bucket_ownership_controls" "pulse3d_uploads_bucket" {
  bucket = aws_s3_bucket.pulse3d_uploads_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "pulse3d_uploads_bucket" {
  bucket = aws_s3_bucket.pulse3d_uploads_bucket.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_acl" "pulse3d_uploads_bucket" {
  depends_on = [aws_s3_bucket_ownership_controls.pulse3d_uploads_bucket]

  bucket = aws_s3_bucket.pulse3d_uploads_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket_cors_configuration" "pulse3d_uploads_bucket" {
  bucket = aws_s3_bucket.pulse3d_uploads_bucket.bucket

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "POST"]
    allowed_origins = var.cluster_name == "prod" ? ["https://dashboard.curibio.com"] : ["https://dashboard.curibio-test.com", "https://dashboard.curibio-modl.com", "http://localhost:3000"]

  }
}
