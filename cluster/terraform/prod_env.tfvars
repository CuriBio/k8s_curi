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
    },
    {
      userarn = "arn:aws:iam::245339368379:user/nikita"
      username = "nikita"
      groups = ["system:masters"]
    }
]

node_groups = {
  medium = {
    desired_capacity = 4
    max_capacity     = 4
    min_capacity     = 1

    instance_types = ["t3a.medium"]
    subnets = ["10.0.1.0/24", "10.0.2.0/24"]

    k8s_labels = {
      # Environment = "prod"
      environment = "prod"
      group = "workers"
    }
    # additional_tags = {
    #   ExtraTag = "example"
    # }
    update_config = {
      max_unavailable_percentage = 50 # or set `max_unavailable`
    }
  },
  argo = {
    desired_capacity = 3
    max_capacity     = 3
    min_capacity     = 1

    instance_types = ["t3a.medium"]
    subnets = ["10.0.3.0/24"]

    k8s_labels = {
      # Environment = "prod"
      environment = "prod"
      group = "argo"
    }
    # additional_tags = {
    #   ExtraTag = "example"
    # }
    update_config = {
      max_unavailable_percentage = 50 # or set `max_unavailable`
    }
  }
}

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
