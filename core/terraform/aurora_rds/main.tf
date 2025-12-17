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
  name        = "${var.name}-parameter-group-pg17"
  family      = "aurora-postgresql17"
  description = "${var.name}-parameter-group"
  tags        = local.tags
}

resource "aws_rds_cluster_parameter_group" "cluster_parameter_group" {
  name        = "${var.name}-cluster-parameter-group-pg17"
  family      = "aurora-postgresql17"
  description = "${var.name}-cluster-parameter-group"
  tags        = local.tags
}

module "db" {
  source = "terraform-aws-modules/rds-aurora/aws"
  version = "~> 9.16"

  name           = var.name
  engine         = "aurora-postgresql"
  engine_version = "17.5"
  instance_class = var.instance_class

  # need atleast two instances for multi-az
  instances = {
    one = {}
    two = {}
  }

  db_subnet_group_name   = var.name
  create_db_subnet_group = true

  subnets                = var.cluster_vpc.private_subnet_ids
  vpc_id                 = var.cluster_vpc.vpc_id
  vpc_security_group_ids = [data.terraform_remote_state.cluster.outputs.sg_worker_group_mgmt_one.id]
  create_security_group  = false
  availability_zones        = var.cluster_vpc.azs

  apply_immediately   = true
  skip_final_snapshot = true
  allow_major_version_upgrade = true

  master_username             = "root"
  master_password             = local.password
  manage_master_user_password = false

  db_parameter_group_name         = aws_db_parameter_group.parameter_group.id
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.cluster_parameter_group.id
  db_cluster_db_instance_parameter_group_name = aws_db_parameter_group.parameter_group.id

  enabled_cloudwatch_logs_exports = ["postgresql"]

  # Enhanced monitoring
  cluster_monitoring_interval = 30
  monitoring_role_arn = aws_iam_role.rds_enhanced_monitoring.arn

  deletion_protection = true

  create_monitoring_role                = false

  tags = local.tags
}

resource "aws_iam_role" "rds_enhanced_monitoring" {
  name_prefix        = "${var.environment}-rds-enhanced-monitoring-"
  assume_role_policy = data.aws_iam_policy_document.rds_enhanced_monitoring.json
}

resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
  role       = aws_iam_role.rds_enhanced_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

data "aws_iam_policy_document" "rds_enhanced_monitoring" {
  statement {
    actions = [
      "sts:AssumeRole",
    ]

    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["monitoring.rds.amazonaws.com"]
    }
  }
}
