cluster_name = "prod-v2"

cluster_env = "prod"

cluster_version          = "1.36"
node_group_version       = "1.35"
ebs_csi_addon_version    = "v1.51.2-eksbuild.1"
kube_proxy_addon_version = "v1.35.3-eksbuild.69"

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
  },
  {
    userarn  = "arn:aws:iam::245339368379:user/james"
    username = "james"
    groups   = ["system:masters"]
  }
]
