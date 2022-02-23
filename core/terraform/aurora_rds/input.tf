variable "instance_class" {
  description = "RDS instance type and size"
  type        = string
}

variable "db_creds_arn" {
  description = "ARN value for db_creds secret"
  type        = string
}
