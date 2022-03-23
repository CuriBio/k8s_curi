output "pulse3d_ecr_repo" {
  description = "pulse3d ECR url"
  value = aws_ecr_repository.pulse3d_ecr_repo.repository_url
}
