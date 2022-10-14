resource "aws_s3_bucket" "workflow_artifacts" {
  bucket = "curi-${var.cluster_name}-workflows"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "workflows_artifacts" {
  bucket = aws_s3_bucket.workflow_artifacts.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_acl" "workflows_artifacts" {
  bucket = aws_s3_bucket.workflow_artifacts.id
  acl    = "private"
}
