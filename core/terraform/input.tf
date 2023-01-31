variable "region" {
  type    = string
  default = "us-east-2"
}

# cluster environment
variable "environment" {
  description = "Environment"
  type        = string
}

# aurora_database inputs
variable "aurora_database_name" {
  description = "Aurora database name"
  type        = string
}

variable "aurora_instance_class" {
  description = "Cluster instance class"
  type        = string
}

variable "password_change_id" {
  type        = string
  description = "Id to trigger changing the master password"
}

