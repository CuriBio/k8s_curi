variable "region" {
  type    = string
  default = "us-east-2"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "private_subnets" {
  type    = list(string)
  default = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnets" {
  type    = list(string)
  default = ["10.0.4.0/24", "10.0.5.0/24", "10.0.6.0/24"]
}

variable "cluster_name" {
  type    = string
  default = "test_cluster"
}

variable "cluster_env" {
  type    = string
  default = "test"
}

variable "cluster_tags" {}

variable "cluster_accounts" {
  default = []
  type    = list(string)
}

variable "cluster_users" {
  default = []
  type = list(object({
    userarn  = string
    username = string
    groups   = list(string)
  }))
}

variable "existing_vpc" {
  description = "Optional: info of an existing VPC to use. If not provided, a new VPC will be created."
  type        = object({
    vpc_id = string
    private_subnet_ids = list(string)
  })
  default     = null
}
