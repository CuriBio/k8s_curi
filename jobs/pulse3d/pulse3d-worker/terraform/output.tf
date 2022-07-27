output "pulse3d_worker_ecr" {
  description = "ECR url"
  value = aws_ecr_repository.pulse3d_worker_ecr.repository_url
}
output "test_output" {}