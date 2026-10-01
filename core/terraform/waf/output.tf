output "api_web_acl_arn" {
  description = "ARN of the REGIONAL (ALB/API) Web ACL."
  value       = aws_wafv2_web_acl.api.arn
}

output "website_web_acl_arn" {
  description = "ARN of the CLOUDFRONT (website) Web ACL — wire into the distribution's web_acl_id."
  value       = aws_wafv2_web_acl.website.arn
}
