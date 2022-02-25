locals {
  name = "${terraform.workspace}-postgres-rds"
  db_creds = jsondecode(
    data.aws_secretsmanager_secret_version.db_creds.secret_string
  )
  tags = {
    Application = "postgres-rds"
    Environment = terraform.workspace
  }
}

// Get data from another state file
data "terraform_remote_state" "state1" {
  backend = "s3"
  config = {
    bucket = "curi-eks-test-cluster-tf-state"
    key    = "cluster/terraform.tfstate"
    region = "us-east-2"
  }
}

resource "aws_db_parameter_group" "parameter_group" {
  name        = "${local.name}-parameter-group"
  family      = "aurora-postgresql13"
  description = "${local.name}-parameter-group"
  tags        = local.tags
}

resource "aws_rds_cluster_parameter_group" "cluster_parameter_group" {
  name        = "${local.name}-cluster-parameter-group"
  family      = "aurora-postgresql13"
  description = "${local.name}-cluster-parameter-group"
  tags        = local.tags
}

# Providing a reference to our default VPC
resource "aws_default_vpc" "default_vpc" {}

# Providing a reference to our default subnets
resource "aws_default_subnet" "default_subnet_a" {
  availability_zone = "us-east-2a"
}

resource "aws_default_subnet" "default_subnet_b" {
  availability_zone = "us-east-2b"
}

data "aws_secretsmanager_secret_version" "db_creds" {
  secret_id = var.db_secret_id
}

module "db" {
  source = "terraform-aws-modules/rds-aurora/aws"

  name           = local.name
  engine         = "aurora-postgresql"
  engine_version = "13.5"
  instance_class = var.instance_class
  instances = {
    one = {}
  }

  subnets                = [aws_default_subnet.default_subnet_a.id, aws_default_subnet.default_subnet_b.id]
  vpc_id                 = data.terraform_remote_state.state1.outputs.vpc_id
  vpc_security_group_ids = [data.terraform_remote_state.state1.outputs.sg_worker_group_mgmt_one_id]
  create_security_group  = false

  apply_immediately   = true
  skip_final_snapshot = true

  master_username        = local.db_creds.username
  master_password        = local.db_creds.password
  create_random_password = false

  db_parameter_group_name         = aws_db_parameter_group.parameter_group.id
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.cluster_parameter_group.id
  # enabled_cloudwatch_logs_exports = ["audit", "error", "general", "slowquery"]

  tags = local.tags
}

resource "aws_secretsmanager_secret" "db_endpoint" {
  name = "db_endpoint"
}

locals {
  db_secrets = {
    port            = module.db.cluster_port
    writer_endpoint = module.db.cluster_endpoint
    reader_endpoint = module.db.cluster_reader_endpoint
  }
}

resource "aws_secretsmanager_secret_version" "db_endpoint" {
  secret_id     = aws_secretsmanager_secret.db_endpoint.id
  secret_string = jsonencode(local.db_secrets)
}
