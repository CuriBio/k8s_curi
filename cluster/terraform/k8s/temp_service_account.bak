resource "kubernetes_namespace" "temp_namespace" {
  metadata {
    annotations = {
      name = "temp namespace"
    }

    name = "temp"
  }
}

resource "aws_iam_role_policy" "temp_pod_iam_role_policy" {
  name        = "TempPodIAMPolicy"
  role        = aws_iam_role.temp_pods.id

  policy = file("${path.module}/temp_namespace_iam_policy.json")
}

data "aws_iam_policy_document" "temp_pods" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(aws_iam_openid_connect_provider.default.url, "https://", "")}:sub"
      values   = ["system:serviceaccount:temp:default"]
    }

    principals {
      identifiers = [aws_iam_openid_connect_provider.default.arn]
      type        = "Federated"
    }
  }
}

resource "aws_iam_role" "temp_pods" {
  name = "temp-pods-iam-role01"

  assume_role_policy = data.aws_iam_policy_document.temp_pods.json
}

resource "kubernetes_default_service_account" "temp_service_account" {
  metadata {
    namespace = "temp"
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.temp_pods.arn
    }
  }
  automount_service_account_token = true
}
