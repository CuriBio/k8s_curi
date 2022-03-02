output "db_name" {
  description = "DB name"
  value       = local.name
}

output "cluster_endpoint" {
  description = "rds writer endpoint"
  value       = module.db.cluster_endpoint
}
