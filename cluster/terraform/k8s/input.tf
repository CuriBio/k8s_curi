variable "region" {
  type    = string
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
variable "env_name" {
  type = string
}

variable "cluster_accounts" {
  default = []
  type    = list(string)
}

variable "cluster_users" {
  type = list(object({
    userarn  = string
    username = string
    groups   = list(string)
  }))
}

variable "private_subnets" {
  type = list(string)
}
