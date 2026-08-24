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
  description = "Id to trigger changing the master password"
  type        = string
}

variable "cluster_vpc" {
  description = "info of an existing VPC to use"
  type        = object({
    vpc_id = string
    private_subnet_ids = list(string)
    azs = list(string)
  })
}

# alb waf
variable "alb_arn" {
  description = "ARN of the ALB to attach the REGIONAL Web ACL to. CONFIGURE."
  type        = string
}
