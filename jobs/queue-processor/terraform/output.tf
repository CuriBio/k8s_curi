output "queue_processor_ecr" {
  description = "ECR url"
  value = aws_ecr_repository.queue_processor_ecr.repository_url
}
