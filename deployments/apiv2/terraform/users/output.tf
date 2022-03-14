output "users_ecr_repo" {
  description = "users ECR url"
  value = aws_ecr_repository.users_ecr_repo.repository_url
}
