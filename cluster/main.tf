terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "4.0.0"
    }

    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "2.8.0"
    }
  }

  required_version = "1.1.0"

  backend "s3" {
  }
}

# Configure the AWS Provider
provider "aws" {
  region  = var.region
}

variable "region" {
  type = string
  default = "us-east-2"
}

variable "vpc_cidr" {
  type = string
  default = "10.0.0.0/16"
}

variable "private_subnets" {
  type = list(string)
  default = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "public_subnets" {
  type = list(string)
  default = ["10.0.4.0/24", "10.0.5.0/24"]
}

variable "cluster_name" {
  type = string
  default = "test_cluster"
}

variable "cluster_tags" {}

data "aws_availability_zones" "available" {}

#####################################################################
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "3.2.0"

  name                 = "${var.cluster_name}-vpc"
  cidr                 = var.vpc_cidr
  azs                  = data.aws_availability_zones.available.names
  private_subnets      = var.private_subnets
  public_subnets       = var.public_subnets
  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true

  tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }

  public_subnet_tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "kubernetes.io/role/elb"                      = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "kubernetes.io/role/internal-elb"             = "1"
  }
}


#####################################################################
resource "aws_security_group" "worker_group_mgmt_one" {
  name_prefix = "worker_group_mgmt_one"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port = 22
    to_port   = 22
    protocol  = "tcp"

    cidr_blocks = [
      "10.0.0.0/8",
    ]
  }
}


resource "aws_security_group" "all_worker_mgmt" {
  name_prefix = "all_worker_management"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port = 22
    to_port   = 22
    protocol  = "tcp"

    cidr_blocks = [
      "10.0.0.0/8",
      "172.16.0.0/12",
      "192.168.0.0/16",
    ]
  }
}

#####################################################################
module "eks_cluster" {
  source = "./k8s"

  cluster_name = var.cluster_name
  cluster_tags = var.cluster_tags

  private_subnets = module.vpc.private_subnets

  region = var.region
  vpc_id = module.vpc.vpc_id

  worker_groups = [
    {
      name                          = "worker-group-1"
      instance_type                 = "t3.small"
      additional_userdata           = ""
      asg_desired_capacity          = 3
      additional_security_group_ids = [aws_security_group.worker_group_mgmt_one.id]
    },
    {
      name                          = "worker-group-2"
      instance_type                 = "t3.medium"
      additional_userdata           = ""
      asg_desired_capacity          = 3
      additional_security_group_ids = [aws_security_group.worker_group_mgmt_one.id]
    },
  ]
}
