data "aws_caller_identity" "current" {}
locals {
    account_id = data.aws_caller_identity.current.account_id
}

# resource "kubernetes_namespace" "pods_namespace" {
#   metadata {
#     annotations = var.namespace_annotations
#     labels = var.namespace_labels
#     name = var.namespace
#   }
# }

resource "aws_iam_role_policy" "namespace_pod_iam_role_policy" {
  name        = var.iam_role_policy_name
  role        = aws_iam_role.pods_iam_role.id

  policy = file("${path.module}/../../json/${var.policy_file_name}")
}

data "aws_iam_policy_document" "pods_iam_policy" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(var.openid_connect_provider.url, "https://", "")}:sub"
      values   = ["system:serviceaccount:${var.namespace}:${var.name}"]
    }

    principals {
      identifiers = [var.openid_connect_provider.arn]
      type        = "Federated"
    }
  }
}

resource "aws_iam_role" "pods_iam_role" {
  name = var.iam_role_name

  assume_role_policy = data.aws_iam_policy_document.pods_iam_policy.json
}

resource "kubernetes_default_service_account" "namespace_service_account" {
  metadata {
    name = "default"
    namespace = var.namespace
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.pods_iam_role.arn
    }
  }
  automount_service_account_token = true
}
