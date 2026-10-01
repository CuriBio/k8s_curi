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

output "api_web_acl_arn" {
  description = "ARN of the REGIONAL (ALB/API) Web ACL."
  value       = module.alb_waf.api_web_acl_arn
}

output "website_web_acl_arn" {
  description = "ARN of the CLOUDFRONT (website) Web ACL — wire into the distribution's web_acl_id."
  value       = module.alb_waf.website_web_acl_arn
}
