variable "name" {
  description = "Cluster name"
  type        = string
}

variable "environment" {
  description = "Cluster environment"
  type        = string
}

variable "instance_class" {
  description = "Cluster instance class"
  type        = string
}

variable "password_change_id" {
  type        = string
  description = "Id to trigger changing the master password"
}

variable "cluster_vpc" {
  description = "info of an existing VPC to use"
  type        = object({
    vpc_id = string
    private_subnet_ids = list(string)
    azs = list(string)
  })
}
