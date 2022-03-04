output "pheno_worker_ecr" {
  description = "ECR url"
  value = aws_ecr_repository.pheno_worker_ecr.repository_url
}
