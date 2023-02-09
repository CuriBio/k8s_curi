resource "aws_s3_bucket" "loki_object_store" {
  bucket = "curi-${var.cluster_name}-loki-logs"
}