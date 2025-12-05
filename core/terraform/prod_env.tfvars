# cluster
environment = "prod"

# database
aurora_database_name  = "prod-curibio"
aurora_instance_class = "db.t3.medium"
password_change_id = "1970-01-03"

cluster_vpc = {
  vpc_id = "vpc-0f627eb26581b01ab"
  private_subnet_ids = [
    "subnet-0c01c53317549fa6a",
    "subnet-03f9095ecd7c1e7fa",
    "subnet-02528348514365028"
  ]
  azs = [
    "us-east-2a",
    "us-east-2b",
    "us-east-2c",
  ]
}
