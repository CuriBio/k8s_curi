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
