output "db_listener_ecr_repo" {
  description = "db listener ECR url"
  value = aws_ecr_repository.db_listener_ecr_repo.repository_url
}
