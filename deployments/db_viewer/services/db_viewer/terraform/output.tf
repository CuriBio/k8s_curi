output "db_viewer_service_ecr" {
  description = "ECR url"
  value = aws_ecr_repository.db_viewer_service_ecr.repository_url
}
