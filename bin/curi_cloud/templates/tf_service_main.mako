resource "aws_ecr_repository" "${service_name}_ecr_repo" {
  name                 = "${service_name}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}
