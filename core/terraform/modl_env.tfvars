# cluster
environment = "modl"

# database
aurora_database_name  = "modl-curibio"
aurora_instance_class = "db.t3.medium"
password_change_id    = "1970-01-03"

cluster_vpc = {
  vpc_id = "vpc-0096fbf0d1c1775fc"
  private_subnet_ids = [
    "subnet-03c66d5fd931efdfa",
    "subnet-0a325720bc2cfd984",
    "subnet-0ae682608b4f78eb0"
  ]
  azs = [
    "us-east-2a",
    "us-east-2b",
    "us-east-2c",
  ]
}
