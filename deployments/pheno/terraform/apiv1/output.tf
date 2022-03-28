output "apiv1_ecr_repo" {
  description = "apiv1 ECR url"
  value = aws_ecr_repository.apiv1_ecr_repo.repository_url
}
