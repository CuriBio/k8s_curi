output "mantarray_ecr_repo" {
  description = "mantarray ECR url"
  value = aws_ecr_repository.mantarray_ecr_repo.repository_url
}
