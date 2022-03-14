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
