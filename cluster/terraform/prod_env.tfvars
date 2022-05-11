cluster_name = "prod"

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
      userarn = "arn:aws:iam::245339368379:user/luci"
      username = "luci"
      groups = ["system:masters"]
    }
]

# worker_groups = [
#   {
#     name                          = "worker-group-1"
#     instance_type                 = "t3.small"
#     additional_userdata           = ""
#     asg_desired_capacity          = 3
#     additional_security_group_ids = [aws_security_group.worker_group_mgmt_one.id]
#     tags = [
#       {
#         key                 = "name"
#         value               = "worker-group-1"
#         propagate_at_launch = true
#       },
#     ]
#   }
# ]
