output "pheno_worker_ecr" {
  description = "ECR url"
  value = aws_ecr_repository.pheno_worker_ecr.repository_url
}

output "remote_pheno_worker" {
  description = "test remote state"
  value = data.terraform_remote_state.state1.outputs
}
