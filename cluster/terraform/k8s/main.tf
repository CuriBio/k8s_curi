resource "aws_iam_role_policy" "aws-loadbalancer-controller" {
  name = "AWSLoadBalancerControllerIAMPolicy"
  role = aws_iam_role.eks_pods.id

  policy = file("${path.module}/json/iam_policy.json")
}

data "aws_iam_policy_document" "eks_pods" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:kube-system:aws-load-balancer-controller"]
    }

    principals {
      identifiers = [module.eks.oidc_provider_arn]
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
    name      = "aws-load-balancer-controller"
    namespace = "kube-system"
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.eks_pods.arn
    }
  }

  automount_service_account_token = true
}

data "aws_iam_policy_document" "workflows_pods" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:argo:argo-workflows-sa"]
    }

    principals {
      identifiers = [module.eks.oidc_provider_arn]
      type        = "Federated"
    }
  }
}

resource "aws_iam_role" "workflow_pods" {
  name = "workflow-pods-iam-role01"

  assume_role_policy = data.aws_iam_policy_document.workflows_pods.json
}


resource "aws_iam_role_policy" "workflow_pod_iam_role_policy" {
  name = "workflow-pods-iam-role01"
  role = aws_iam_role.workflow_pods.id

  policy = file("${path.module}/json/argo_namespace_iam_policy.json")
}

resource "aws_iam_role_policy" "pulse3d_pod_iam_role_policy" {
  name = "pulse3d-pods-iam-role01"
  role = aws_iam_role.pulse3d_pods.id

  policy = file("${path.module}/json/pulse3d_${var.cluster_name}_iam_policy.json")
}

data "aws_iam_policy_document" "pulse3d_pods" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:pulse3d:default"]
    }

    principals {
      identifiers = [module.eks.oidc_provider_arn]
      type        = "Federated"
    }
  }
}

resource "aws_iam_role" "pulse3d_pods" {
  name = "pulse3d-pods-iam-role01"

  assume_role_policy = data.aws_iam_policy_document.pulse3d_pods.json
}

resource "aws_iam_role_policy" "apiv2_pod_iam_role_policy" {
  name = "apiv2-pods-iam-role01"
  role = aws_iam_role.apiv2_pods.id

  policy = file("${path.module}/json/apiv2_${var.cluster_name}_iam_policy.json")
}

data "aws_iam_policy_document" "apiv2_pods" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:apiv2:default"]
    }

    principals {
      identifiers = [module.eks.oidc_provider_arn]
      type        = "Federated"
    }
  }
}

resource "aws_iam_role" "apiv2_pods" {
  name = "apiv2-pods-iam-role01"

  assume_role_policy = data.aws_iam_policy_document.apiv2_pods.json
}

data "aws_iam_policy_document" "loki_pods" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:argocd:default"]
    }

    principals {
      identifiers = [module.eks.oidc_provider_arn]
      type        = "Federated"
    }
  }
}

resource "aws_iam_role" "loki_pods" {
  name = "loki-pods-iam-role01"

  assume_role_policy = data.aws_iam_policy_document.loki_pods.json
}
resource "aws_iam_role_policy" "loki_pod_iam_role_policy" {
  name = "loki-pods-iam-role01"
  role = aws_iam_role.loki_pods.id

  policy = file("${path.module}/json/loki_${var.cluster_name}_iam_policy.json")
}
data "aws_iam_policy_document" "operators_pods" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:kopf:operator"]
    }

    principals {
      identifiers = [module.eks.oidc_provider_arn]
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

module "argo_workflows" {
  source       = "./modules/argo_workflows"
  cluster_name = var.cluster_name
}

module "loki_logs_bucket" {
  source       = "./modules/grafana-loki"
  cluster_name = var.cluster_name
}

module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  version         = "19.15.3"
  cluster_name    = var.cluster_name
  cluster_version = "1.27"
  subnet_ids      = var.private_subnets

  tags   = var.cluster_tags
  vpc_id = var.vpc_id

  aws_auth_accounts              = var.cluster_accounts
  aws_auth_users                 = var.cluster_users
  manage_aws_auth_configmap      = true
  cluster_endpoint_public_access = true
  custom_oidc_thumbprints        = [data.external.thumbprint.result.thumbprint]

  eks_managed_node_groups = {
    medium = {
      desired_size = 3
      min_size     = 1
      max_size     = 3

      instance_types = ["t3a.medium"]
      subnet_ids     = [var.private_subnets[0], var.private_subnets[1]]

      labels = {
        group = "services"
      }
      update_config = {
        max_unavailable_percentage = 50 # or set `max_unavailable`
      }
    },

    workers = {
      desired_size = 3
      min_size     = 1
      max_size     = 3

      instance_types = ["c6a.large"]
      subnet_ids     = [var.private_subnets[0], var.private_subnets[1]]

      labels = {
        group = "workers"
      }
      update_config = {
        max_unavailable_percentage = 50 # or set `max_unavailable`
      }
    },
    argo = {
      desired_size = 3
      min_size     = 1
      max_size     = 3

      instance_types = ["t3a.medium"]
      subnet_ids     = [var.private_subnets[2]]

      labels = {
        group = "argo"
      }
      update_config = {
        max_unavailable_percentage = 50 # or set `max_unavailable`
      }
    }
  }
}

data "aws_eks_cluster" "cluster" {
  name = module.eks.cluster_name
}


data "aws_eks_cluster_auth" "cluster" {
  name = module.eks.cluster_name
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

