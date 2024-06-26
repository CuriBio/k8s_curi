cluster_name = "test-v2"

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
