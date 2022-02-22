output "${service_name}_ecr_repo" {
  description = "${service_name} ECR url"
  value = aws_ecr_repository.${service_name}_ecr_repo.repository_url
}
