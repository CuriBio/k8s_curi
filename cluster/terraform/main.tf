terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.40.0"
    }

    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "2.21.1"
    }
  }

  required_version = "1.5.2"

  backend "s3" {}
}

# Configure the AWS Provider
provider "aws" {
  region = var.region
}


data "aws_availability_zones" "available" {}

#####################################################################
locals {
  create_new_vpc = var.existing_vpc == null
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  count = local.create_new_vpc ? 1 : 0

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
  }

  public_subnet_tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "kubernetes.io/role/elb"                    = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "kubernetes.io/role/internal-elb"           = "1"
  }
}

data "aws_vpc" "selected_vpc" {
  count = local.create_new_vpc ? 0 : 1
  id = var.existing_vpc.vpc_id
}

data "aws_subnet" "private_subnet_0" {
  count = local.create_new_vpc ? 0 : 1
  id = var.existing_vpc.private_subnet_ids[0]
}
data "aws_subnet" "private_subnet_1" {
  count = local.create_new_vpc ? 0 : 1
  id = var.existing_vpc.private_subnet_ids[1]
}
data "aws_subnet" "private_subnet_2" {
  count = local.create_new_vpc ? 0 : 1
  id = var.existing_vpc.private_subnet_ids[2]
}

locals {
  vpc = local.create_new_vpc ? module.vpc[0] : data.aws_vpc.selected_vpc[0]
  vpc_id = local.create_new_vpc ? module.vpc[0].vpc_id : data.aws_vpc.selected_vpc[0].id
  vpc_private_subnets = local.create_new_vpc ? module.vpc[0].private_subnets : [
    data.aws_subnet.private_subnet_0[0].id,
    data.aws_subnet.private_subnet_1[0].id,
    data.aws_subnet.private_subnet_2[0].id,
  ]
}


#####################################################################
resource "aws_security_group" "worker_group_mgmt_one" {
  name_prefix = "worker_group_mgmt_one"
  vpc_id      = local.vpc_id

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
  vpc_id      = local.vpc_id

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
  private_subnets  = local.vpc_private_subnets
  vpc_id           = local.vpc_id
  node_groups = {
    services = {
      desired_size = 1
      min_size     = 1
      max_size     = 3

      ami_type = "AL2023_x86_64_STANDARD"
      instance_types = ["t3a.medium"]
      subnet_ids     = [local.vpc_private_subnets[0], local.vpc_private_subnets[1]]

      labels = {
        group = "services"
      }
      update_config = {
        max_unavailable_percentage = 50 # or set `max_unavailable`
      }

      block_device_mappings = {
        xdva = {
          device_name = "/dev/xvda"

          ebs = {
            volume_size           = 20
            volume_type           = "gp2"
            delete_on_termination = true
          }
        }
      }
    },

    workers = {
      desired_size = 0
      min_size     = 0
      max_size     = 10

      ami_type = "AL2023_x86_64_STANDARD"
      instance_types = ["c6a.xlarge"]
      subnet_ids     = [local.vpc_private_subnets[0], local.vpc_private_subnets[1]]

      labels = {
        group = "workers"
      }
      update_config = {
        max_unavailable_percentage = 50 # or set `max_unavailable`
      }

      block_device_mappings = {
        xdva = {
          device_name = "/dev/xvda"

          ebs = {
            volume_size           = 200
            volume_type           = "gp3"
            delete_on_termination = true
          }
        }
      }
    },
    argo = {
      desired_size = 2
      min_size     = 1
      max_size     = 3

      ami_type = "AL2023_x86_64_STANDARD"
      instance_types = ["t3a.medium"]
      subnet_ids     = [local.vpc_private_subnets[2]]

      labels = {
        group = "argo"
      }
      update_config = {
        max_unavailable_percentage = 50 # or set `max_unavailable`
      }

      block_device_mappings = {
        xdva = {
          device_name = "/dev/xvda"

          ebs = {
            volume_size           = 20
            volume_type           = "gp2"
            delete_on_termination = true
          }
        }
      }
    }
  }
}
