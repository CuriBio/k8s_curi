output "db-viewer_service_ecr" {
  description = "ECR url"
  value       = aws_ecr_repository.db-viewer_service_ecr.repository_url
}
