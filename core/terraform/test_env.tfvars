# cluster
environment = "test"

# database
aurora_database_name  = "test-curibio"
aurora_instance_class = "db.t3.medium"
password_change_id = "2023-01-31"

cluster_vpc = {
  vpc_id = "vpc-0c481f70e775c783e"
  private_subnet_ids = [
    "subnet-0014feda1d099ef21",
    "subnet-02ddc001c731f2d82",
    "subnet-0155b2de78e9b0086"
  ]
  azs = [
    "us-east-2a",
    "us-east-2b",
    "us-east-2c",
  ]
}
