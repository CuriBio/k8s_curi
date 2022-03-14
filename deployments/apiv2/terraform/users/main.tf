resource "aws_ecr_repository" "users_ecr_repo" {
  name                 = "users"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}
