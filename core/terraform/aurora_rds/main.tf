resource "random_password" "adminpassword" {
  for_each = toset([var.password_change_id])
  length   = 32
  special  = false
}

locals {
  password = random_password.adminpassword[var.password_change_id].result

  tags = {
    Application = "postgres-rds"
    Environment = var.environment
  }
}

// Get data from another state file
data "terraform_remote_state" "cluster" {
  backend = "s3"
  config = {
    bucket = "curi-eks-${var.environment}-cluster-tf-state"
    key    = "cluster/terraform.tfstate"
    region = "us-east-2"
  }
}

resource "aws_db_parameter_group" "parameter_group" {
  name        = "${var.name}-parameter-group"
  family      = "aurora-postgresql13"
  description = "${var.name}-parameter-group"
  tags        = local.tags
}

resource "aws_rds_cluster_parameter_group" "cluster_parameter_group" {
  name        = "${var.name}-cluster-parameter-group"
  family      = "aurora-postgresql13"
  description = "${var.name}-cluster-parameter-group"
  tags        = local.tags
}

module "db" {
  source = "terraform-aws-modules/rds-aurora/aws"

  name           = var.name
  engine         = "aurora-postgresql"
  engine_version = "13.5"
  instance_class = var.instance_class
  instances = {
    one = {}
  }

  subnets                = data.terraform_remote_state.cluster.outputs.cluster_vpc.private_subnets
  vpc_id                 = data.terraform_remote_state.cluster.outputs.cluster_vpc.vpc_id
  vpc_security_group_ids = [data.terraform_remote_state.cluster.outputs.sg_worker_group_mgmt_one.id]
  create_security_group  = false

  apply_immediately   = true
  skip_final_snapshot = true

  master_username        = "root"
  master_password        = local.password
  create_random_password = false

  db_parameter_group_name         = aws_db_parameter_group.parameter_group.id
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.cluster_parameter_group.id
  # enabled_cloudwatch_logs_exports = ["audit", "error", "general", "slowquery"]

  tags = local.tags
}

