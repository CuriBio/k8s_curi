resource "aws_ecr_repository" "mantarray_ecr_repo" {
  name                 = "mantarray"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}
