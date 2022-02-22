
output "${service_name}_ecr_repo" {
  description = "${service_name} ecr repository"
  value       = module.${service_name}.${service_name}_ecr_repo
}
