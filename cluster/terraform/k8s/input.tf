variable "region" {
  type = string
  default = "us-east-2"
}

variable "vpc_id" {
  type = string
}

variable "cluster_tags" {
  type = map(any)
}

variable "cluster_name" {
  type = string
}

variable "worker_groups" {
  type = list(object({
    name                  = string
    instance_type         = string
    additional_userdata   = string
    asg_desired_capacity  = number

    additional_security_group_ids = list(any)
  }))
}

variable "cluster_accounts" {
  default = []
  type    = list(string)
}

variable "cluster_users" {
  type = list(object({
    userarn   = string
    username  = string
    groups    = list(string)
  }))
}

variable "private_subnets" {
  type = list(string)
}
