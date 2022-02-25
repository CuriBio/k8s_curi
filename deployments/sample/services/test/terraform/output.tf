output "test_service_ecr" {
  description = "ECR url"
  value = aws_ecr_repository.test_service_ecr.repository_url
}

output "remote_test" {
  description = "test remote state"
  value = data.terraform_remote_state.state1.outputs.vpc_id
}
