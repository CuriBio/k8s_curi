output "sg_worker_group_mgmt_one" {
  description = "worker_group_mgmt_one security group"
  value = aws_security_group.worker_group_mgmt_one
}

output "sg_all_worker_mgmt" {
  description = "all_worker_management security group"
  value = aws_security_group.all_worker_mgmt
}
