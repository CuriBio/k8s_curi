output "${service_name}_service_ecr" {
  description = "ECR url"
  value = aws_ecr_repository.${service_name}_service_ecr.repository_url
}
