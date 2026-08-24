variable "cluster_name" {
  type = string
  default = "test_cluster"
}

variable "region" {
  type    = string
  default = "us-east-2"
}

variable "domain_name" {
  type = string
  default = "curibio-test.com"
}

variable "website_waf_web_acl" {
  type = string
}
