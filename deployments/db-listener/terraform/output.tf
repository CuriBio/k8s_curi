/*
* variable ??? {
*  type = ???
*  default = ???
*}
*/

output "db_listener_ecr_repo" {
  description = "db_listener ecr repository"
  value       = module.db_listener.db_listener_ecr_repo
}
