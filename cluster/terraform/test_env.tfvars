cluster_name = "test-v2-new"

cluster_env = "test"

cluster_tags = {
  Environment = "test"
}

cluster_accounts = [
  077346344852
]

cluster_users = [
  {
    userarn  = "arn:aws:iam::077346344852:user/jason"
    username = "jason"
    groups   = ["system:masters"]
  },
  {
    userarn  = "arn:aws:iam::077346344852:user/tanner"
    username = "tanner"
    groups   = ["system:masters"]
  },
  {
    userarn  = "arn:aws:iam::077346344852:user/roberto"
    username = "roberto"
    groups   = ["system:masters"]
  }
]

existing_vpc = {
  vpc_id = "vpc-0c481f70e775c783e"
  private_subnet_ids = [
    "subnet-0014feda1d099ef21",
    "subnet-02ddc001c731f2d82",
    "subnet-0155b2de78e9b0086"
  ]
}
