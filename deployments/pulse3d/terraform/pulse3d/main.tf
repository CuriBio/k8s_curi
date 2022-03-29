resource "aws_ecr_repository" "pulse3d_ecr_repo" {
  name                 = "pulse3d_api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}
