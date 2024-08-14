output "hermes_worker_ecr" {
  description = "ECR url"
  value = aws_ecr_repository.hermes_worker_ecr.repository_url
}
