resource "aws_iam_role_policy" "loki_pod_iam_role_policy" {
  name        = "pulse3d-pods-iam-role01"
  role        = aws_iam_role.loki_pods.id

  policy = file("${path.module}/json/loki_${var.cluster_name}_iam_policy.json")
}

data "aws_iam_policy_document" "loki_pods" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(aws_iam_openid_connect_provider.default.url, "https://", "")}:sub"
      values   = ["system:serviceaccount:loki:default"]
    }

    principals {
      identifiers = [aws_iam_openid_connect_provider.default.arn]
      type        = "Federated"
    }
  }
}

resource "aws_iam_role" "loki_pods" {
  name = "loki-pods-iam-role01"

  assume_role_policy = data.aws_iam_policy_document.loki.json
}

resource "aws_iam_role_policy" "aws-loadbalancer-controller" {
  name        = "AWSLoadBalancerControllerIAMPolicy"
  role        = aws_iam_role.eks_pods.id

  policy = file("${path.module}/json/iam_policy.json")
}

data "aws_iam_policy_document" "eks_pods" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(aws_iam_openid_connect_provider.default.url, "https://", "")}:sub"
      values   = ["system:serviceaccount:kube-system:aws-load-balancer-controller"]
    }

    principals {
      identifiers = [aws_iam_openid_connect_provider.default.arn]
      type        = "Federated"
    }
  }
}

resource "aws_iam_role" "eks_pods" {
  name = "eks-pods-iam-role01"

  assume_role_policy = data.aws_iam_policy_document.eks_pods.json
}

resource "kubernetes_service_account" "service_account" {
  metadata {
    name = "aws-load-balancer-controller"
    namespace = "kube-system"
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.eks_pods.arn
    }
  }
  automount_service_account_token = true
}


resource "aws_iam_role_policy" "workflow_pod_iam_role_policy" {
  name        = "workflow-pods-iam-role01"
  role        = aws_iam_role.workflow_pods.id

  policy = file("${path.module}/json/argo_namespace_iam_policy.json")
}

data "aws_iam_policy_document" "workflows_pods" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(aws_iam_openid_connect_provider.default.url, "https://", "")}:sub"
      values   = ["system:serviceaccount:argo:argo-workflows-sa"]
    }

    principals {
      identifiers = [aws_iam_openid_connect_provider.default.arn]
      type        = "Federated"
    }
  }
}

resource "aws_iam_role" "workflow_pods" {
  name = "workflow-pods-iam-role01"

  assume_role_policy = data.aws_iam_policy_document.workflows_pods.json
}



resource "aws_iam_role_policy" "pulse3d_pod_iam_role_policy" {
  name        = "pulse3d-pods-iam-role01"
  role        = aws_iam_role.pulse3d_pods.id

  policy = file("${path.module}/json/pulse3d_${var.cluster_name}_iam_policy.json")
}

data "aws_iam_policy_document" "pulse3d_pods" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(aws_iam_openid_connect_provider.default.url, "https://", "")}:sub"
      values   = ["system:serviceaccount:pulse3d:default"]
    }

    principals {
      identifiers = [aws_iam_openid_connect_provider.default.arn]
      type        = "Federated"
    }
  }
}

resource "aws_iam_role" "pulse3d_pods" {
  name = "pulse3d-pods-iam-role01"

  assume_role_policy = data.aws_iam_policy_document.pulse3d_pods.json
}

resource "aws_iam_role_policy" "apiv2_pod_iam_role_policy" {
  name        = "apiv2-pods-iam-role01"
  role        = aws_iam_role.apiv2_pods.id

  policy = file("${path.module}/json/apiv2_${var.cluster_name}_iam_policy.json")
}

data "aws_iam_policy_document" "apiv2_pods" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(aws_iam_openid_connect_provider.default.url, "https://", "")}:sub"
      values   = ["system:serviceaccount:apiv2:default"]
    }

    principals {
      identifiers = [aws_iam_openid_connect_provider.default.arn]
      type        = "Federated"
    }
  }
}

resource "aws_iam_role" "apiv2_pods" {
  name = "apiv2-pods-iam-role01"

  assume_role_policy = data.aws_iam_policy_document.apiv2_pods.json
}

# resource "aws_iam_role_policy" "operators_iam_role_policy" {
#   name        = "operators-iam-role01"
#   role        = aws_iam_role.operators_pods.id

#   policy = file("${path.module}/json/operators_${var.cluster_name}_iam_policy.json")
# }

data "aws_iam_policy_document" "operators_pods" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(aws_iam_openid_connect_provider.default.url, "https://", "")}:sub"
      values   = ["system:serviceaccount:kopf:operator"]
    }

    principals {
      identifiers = [aws_iam_openid_connect_provider.default.arn]
      type        = "Federated"
    }
  }
}

resource "aws_iam_role" "operators_pods" {
  name = "operators-iam-role01"

  assume_role_policy = data.aws_iam_policy_document.operators_pods.json
}

data "aws_region" "current" {}
data "external" "thumbprint" {
  program = ["/bin/sh", "${path.module}/external/thumbprint.sh", data.aws_region.current.name]
}

resource "aws_iam_openid_connect_provider" "default" {
  url = module.eks.cluster_oidc_issuer_url
  client_id_list  = ["sts.amazonaws.com" ]
  thumbprint_list = [data.external.thumbprint.result.thumbprint]
}

module "argo_workflows" {
  source = "./modules/argo_workflows"
  cluster_name = var.cluster_name
}

module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  version         = "17.24.0"
  cluster_name    = var.cluster_name
  cluster_version = "1.21"
  subnets         = var.private_subnets

  tags    = var.cluster_tags
  vpc_id  = var.vpc_id

  map_accounts  = var.cluster_accounts
  map_users     = var.cluster_users

  node_groups = {
    medium = {
      desired_capacity = 8
      max_capacity     = 10
      min_capacity     = 1

      instance_types = ["t3a.medium"]
      subnets = [var.private_subnets[0], var.private_subnets[1]]

      k8s_labels = {
        group = "workers"
      }
      update_config = {
        max_unavailable_percentage = 50 # or set `max_unavailable`
      }
    },
    argo = {
      desired_capacity = 3
      max_capacity     = 3
      min_capacity     = 1

      instance_types = ["t3a.medium"]
      subnets = [var.private_subnets[2]]

      k8s_labels = {
        group = "argo"
      }
      update_config = {
        max_unavailable_percentage = 50 # or set `max_unavailable`
      }
    }
  }
}


data "aws_eks_cluster" "cluster" {
  name = module.eks.cluster_id
}


data "aws_eks_cluster_auth" "cluster" {
  name = module.eks.cluster_id
}


# Kubernetes provider
# https://learn.hashicorp.com/terraform/kubernetes/provision-eks-cluster#optional-configure-terraform-kubernetes-provider
# To learn how to schedule deployments and services using the provider,
# go here: https://learn.hashicorp.com/terraform/kubernetes/deploy-nginx-kubernetes

# The Kubernetes provider is included in this file so the EKS module can complete successfully.
# Otherwise, it throws an error when creating `kubernetes_config_map.aws_auth`.
# You should **not** schedule deployments and services in this workspace. This keeps workspaces
# modular (one for provision EKS, another for scheduling Kubernetes resources) as per best practices.

provider "kubernetes" {
  host                   = data.aws_eks_cluster.cluster.endpoint
  token                  = data.aws_eks_cluster_auth.cluster.token
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.cluster.certificate_authority.0.data)
}

