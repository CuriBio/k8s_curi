resource "aws_ecr_repository" "mantarray_ecr_repo" {
  name                 = "mantarray"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_s3_bucket" "main_firmware_bucket" {
  bucket = "${var.cluster_name}-main-firmware"
}

resource "aws_s3_bucket_policy" "main_firmware_bucket" {
    bucket = aws_s3_bucket.main_firmware_bucket.id
    policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Sid       = "EnforceTls"
                Effect    = "Deny"
                Principal = "*"
                Action    = "s3:*"
                Resource = [
                    "${aws_s3_bucket.main_firmware_bucket.arn}/*",
                    "${aws_s3_bucket.main_firmware_bucket.arn}",
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

resource "aws_s3_bucket_ownership_controls" "main_firmware_bucket" {
  bucket = aws_s3_bucket.main_firmware_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "main_firmware_bucket" {
  bucket = aws_s3_bucket.main_firmware_bucket.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_acl" "main_firmware_bucket" {
  depends_on = [aws_s3_bucket_ownership_controls.main_firmware_bucket]

  bucket = aws_s3_bucket.main_firmware_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket" "channel_firmware_bucket" {
  bucket = "${var.cluster_name}-channel-firmware"
}

resource "aws_s3_bucket_policy" "channel_firmware_bucket" {
    bucket = aws_s3_bucket.channel_firmware_bucket.id
    policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Sid       = "EnforceTls"
                Effect    = "Deny"
                Principal = "*"
                Action    = "s3:*"
                Resource = [
                    "${aws_s3_bucket.channel_firmware_bucket.arn}/*",
                    "${aws_s3_bucket.channel_firmware_bucket.arn}",
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

resource "aws_s3_bucket_ownership_controls" "channel_firmware_bucket" {
  bucket = aws_s3_bucket.channel_firmware_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "channel_firmware_bucket" {
  bucket = aws_s3_bucket.channel_firmware_bucket.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_acl" "channel_firmware_bucket" {
  depends_on = [aws_s3_bucket_ownership_controls.channel_firmware_bucket]

  bucket = aws_s3_bucket.channel_firmware_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket" "logs_bucket" {
  bucket = "${var.cluster_name}-mantarray-logs"
}

resource "aws_s3_bucket_policy" "logs_bucket" {
    bucket = aws_s3_bucket.logs_bucket.id
    policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Sid       = "EnforceTls"
                Effect    = "Deny"
                Principal = "*"
                Action    = "s3:*"
                Resource = [
                    "${aws_s3_bucket.logs_bucket.arn}/*",
                    "${aws_s3_bucket.logs_bucket.arn}",
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

resource "aws_s3_bucket_ownership_controls" "logs_bucket" {
  bucket = aws_s3_bucket.logs_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs_bucket" {
  bucket = aws_s3_bucket.logs_bucket.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_acl" "logs_bucket" {
  depends_on = [aws_s3_bucket_ownership_controls.logs_bucket]

  bucket = aws_s3_bucket.logs_bucket.id
  acl    = "private"
}
