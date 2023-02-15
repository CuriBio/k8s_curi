output "jobs_operator_ecr" {
  description = "ECR url"
  value = aws_ecr_repository.jobs_operator_ecr.repository_url
}
