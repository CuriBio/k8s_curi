cluster_name = "prod-v2"

cluster_env = "prod"
cluster_tags = {
  Environment = "prod cluster"
}

cluster_accounts = [
  245339368379
]

cluster_users = [
  {
    userarn  = "arn:aws:iam::245339368379:user/jason"
    username = "jason"
    groups   = ["system:masters"]
  },
  {
    userarn  = "arn:aws:iam::245339368379:user/tanner"
    username = "tanner"
    groups   = ["system:masters"]
  },
  {
    userarn  = "arn:aws:iam::245339368379:user/roberto"
    username = "roberto"
    groups   = ["system:masters"]
  }
]
