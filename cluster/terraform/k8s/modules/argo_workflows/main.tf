resource "aws_s3_bucket" "workflow_artifacts" {
  bucket = "curi-${var.cluster_name}-workflows"
}

resource "aws_s3_bucket_ownership_controls" "workflow_artifacts" {
  bucket = aws_s3_bucket.workflow_artifacts.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "workflow_artifacts" {
  bucket = aws_s3_bucket.workflow_artifacts.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_acl" "workflow_artifacts" {
  depends_on = [aws_s3_bucket_ownership_controls.workflow_artifacts]

  bucket = aws_s3_bucket.workflow_artifacts.id
  acl    = "private"
}
