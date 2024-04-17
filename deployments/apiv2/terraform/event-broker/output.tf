output "event_broker_ecr_repo" {
  description = "event_broker ECR url"
  value = aws_ecr_repository.event_broker_ecr_repo.repository_url
}
