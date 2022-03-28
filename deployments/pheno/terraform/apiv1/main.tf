resource "aws_ecr_repository" "apiv1_ecr_repo" {
  name                 = "pheno/apiv1"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}
