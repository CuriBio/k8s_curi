variable "name" {
  type = string
  default = "default"
}

variable "namespace" {
  type = string
}

variable "policy_file_name" {
  type = string
}

variable "iam_role_name" {
  type = string
}

variable "iam_role_policy_name" {
  type = string
}

variable "namespace_annotations" {
  type = map(any)
  default = {}
}

variable "namespace_labels" {
  type = map(any)
  default = {}
}

variable "openid_connect_provider" {
}
