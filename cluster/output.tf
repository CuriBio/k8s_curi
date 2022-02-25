output "sg_worker_group_mgmt_one" {
  description = "worker_group_mgmt_one security group arn"
  value = aws_security_group.worker_group_mgmt_one.arn
}

output "sg_all_worker_mgmt" {
  description = "all_worker_management security group arn"
  value = aws_security_group.all_worker_mgmt.arn
}

output "vpc_id" {
  description = "cluster vpc id"
  value = module.vpc.vpc_id
}

output "vpc_private_subnet_ids" {
  description = "private vpc subnet ids"
  value = module.vpc.private_subnets
}
