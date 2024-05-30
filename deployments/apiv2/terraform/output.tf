/*
* variable ??? {
*  type = ???
*  default = ???
*}
*/

output "users_ecr_repo" {
  description = "users ecr repository"
  value       = module.users.users_ecr_repo
}

output "mantarray_ecr_repo" {
  description = "mantarray ecr repository"
  value       = module.mantarray.mantarray_ecr_repo
}


output "event_broker_ecr_repo" {
  description = "event broker ecr repository"
  value       = module.event_broker.event_broker_ecr_repo
}
