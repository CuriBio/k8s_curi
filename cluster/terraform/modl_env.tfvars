cluster_name = "modl-v2"
cluster_env  = "modl"
cluster_tags = {
  Environment = "modl cluster"
}

cluster_accounts = [
  725604423866
]

cluster_users = [

  {
    userarn  = "arn:aws:iam::725604423866:user/jason"
    username = "jason"
    groups   = ["system:masters"]
  },
  {
    userarn  = "arn:aws:iam::725604423866:user/tanner"
    username = "tanner"
    groups   = ["system:masters"]
  },
  {
    userarn  = "arn:aws:iam::725604423866:user/roberto"
    username = "roberto"
    groups   = ["system:masters"]
  }
]
