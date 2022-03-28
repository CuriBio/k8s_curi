/*
* variable ??? {
*  type = ???
*  default = ???
*}
*/

output "apiv1_ecr_repo" {
  description = "apiv1 ecr repository"
  value       = module.apiv1.apiv1_ecr_repo
}
