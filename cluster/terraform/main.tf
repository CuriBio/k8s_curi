terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.7.0"
    }

    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "2.21.1"
    }
  }

  required_version = "1.5.2"

  backend "s3" {
  }
}

# Configure the AWS Provider
provider "aws" {
  region = var.region
}


data "aws_availability_zones" "available" {}

#####################################################################
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name                 = "${var.cluster_env}-vpc"
  cidr                 = var.vpc_cidr
  azs                  = data.aws_availability_zones.available.names
  private_subnets      = var.private_subnets
  public_subnets       = var.public_subnets
  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true

  tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "kubernetes.io/cluster/prod"                = "shared"
  }

  public_subnet_tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "kubernetes.io/cluster/prod"                = "shared"
    "kubernetes.io/role/elb"                    = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/cluster/prod"                = "shared"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "kubernetes.io/role/internal-elb"           = "1"
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

  ingress {
    from_port = 5432
    to_port   = 5432
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
module "eks_cluster_v2" {
  source = "./k8s"

  region           = var.region
  cluster_env      = var.cluster_env
  cluster_name     = var.cluster_name
  cluster_tags     = var.cluster_tags
  cluster_users    = var.cluster_users
  cluster_accounts = var.cluster_accounts
  private_subnets  = module.vpc.private_subnets
  vpc_id           = module.vpc.vpc_id
  node_groups = {
    services = {
      desired_size = 3
      min_size     = 1
      max_size     = 3

      instance_types = ["t3a.medium"]
      subnet_ids     = [module.vpc.private_subnets[0], module.vpc.private_subnets[1]]

      labels = {
        group = "services"
      }
      update_config = {
        max_unavailable_percentage = 50 # or set `max_unavailable`
      }
    },

    workers = {
      desired_size = 3
      min_size     = 1
      max_size     = 3

      instance_types = ["c6a.large"]
      subnet_ids     = [module.vpc.private_subnets[0], module.vpc.private_subnets[1]]

      labels = {
        group = "workers"
      }
      update_config = {
        max_unavailable_percentage = 50 # or set `max_unavailable`
      }
    },
    argo = {
      desired_size = 3
      min_size     = 1
      max_size     = 3

      instance_types = ["t3a.medium"]
      subnet_ids     = [module.vpc.private_subnets[2]]

      labels = {
        group = "argo"
      }
      update_config = {
        max_unavailable_percentage = 50 # or set `max_unavailable`
      }
    }
  }
}

