output "aurora_database_name" {
  description = "Aurora rds name"
  value       = module.aurora_database.db_name
}

output "aurora_database_endpoint" {
  description = "Aurora database endpoint"
  value       = module.aurora_database.cluster_endpoint
}

output "aurora_database_password" {
  description = "Aurora database password"
  sensitive   = true
  value       = module.aurora_database.root_password
}
