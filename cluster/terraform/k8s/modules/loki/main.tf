resource "aws_s3_bucket" "loki_logs_bucket" {
  bucket = "${var.cluster_name}-loki-logs"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "loki_logs_bucket" {
  bucket = aws_s3_bucket.loki_logs_bucket.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_acl" "loki_logs_bucket" {
  bucket = aws_s3_bucket.loki_logs_bucket.id
  acl    = "private"
}