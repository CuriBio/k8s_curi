output "advanced_analysis_ecr_repo" {
  description = "advanced analysis ECR url"
  value = aws_ecr_repository.advanced_analysis_ecr_repo.repository_url
}
