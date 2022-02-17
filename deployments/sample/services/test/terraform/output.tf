output "test_service_ecr" {
  description = "ECR url"
  value = aws_ecr_repository.test_service_ecr.repository_url
}
