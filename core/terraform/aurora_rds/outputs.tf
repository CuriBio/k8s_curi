output "db_name" {
  description = "DB name"
  value       = var.name
}

output "cluster_endpoint" {
  description = "rds writer endpoint"
  value       = module.db.cluster_endpoint
}

output "root_password" {
  description = "Root database password"
  sensitive   = true
  value       = local.password
}
