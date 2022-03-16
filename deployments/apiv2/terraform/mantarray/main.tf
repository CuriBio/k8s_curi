resource "aws_ecr_repository" "mantarray_ecr_repo" {
  name                 = "mantarray"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_s3_bucket" "main_firmware_bucket" {
  bucket = "main-firmware"
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
  bucket = aws_s3_bucket.main_firmware_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket" "channel_firmware_bucket" {
  bucket = "channel-firmware"
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
  bucket = aws_s3_bucket.channel_firmware_bucket.id
  acl    = "private"
}
