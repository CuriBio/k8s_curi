resource "aws_ecr_repository" "advanced_analysis_ecr_repo" {
  name                 = "advanced_analysis_api"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "advanced_analysis_ecr_lifecycle_policy" {
  repository = aws_ecr_repository.advanced_analysis_ecr_repo.name

  policy = <<EOF
{
    "rules": [
        {
            "rulePriority": 1,
            "description": "Keep last 3 tagged images",
            "selection": {
                "tagStatus": "tagged",
                "tagPrefixList": ["0"],
                "countType": "imageCountMoreThan",
                "countNumber": 3
            },
            "action": {
                "type": "expire"
            }
        },
        {
            "rulePriority": 2,
            "description": "Keep only 1 untagged image",
            "selection": {
                "tagStatus": "untagged",
                "countType": "imageCountMoreThan",
                "countNumber": 1
            },
            "action": {
                "type": "expire"
            }
        }
    ]
}
EOF
}
