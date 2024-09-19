output "advanced_analysis_worker_ecr" {
  description = "ECR url"
  value = aws_ecr_repository.advanced_analysis_worker_ecr.repository_url
}
