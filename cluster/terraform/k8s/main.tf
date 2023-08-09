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
  name = "${var.cluster_name}-eks-pods-iam-role01"

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
  name = "${var.cluster_name}-workflow-pods-iam-role01"

  assume_role_policy = data.aws_iam_policy_document.workflows_pods.json
}


resource "aws_iam_role_policy" "workflow_pod_iam_role_policy" {
  name = "${var.cluster_name}-workflow-pods-iam-role01"
  role = aws_iam_role.workflow_pods.id

  policy = file("${path.module}/json/argo_ns_${var.cluster_env}_iam_policy.json")
}

resource "aws_iam_role_policy" "pulse3d_pod_iam_role_policy" {
  name = "${var.cluster_name}-pulse3d-pods-iam-role01"
  role = aws_iam_role.pulse3d_pods.id

  policy = file("${path.module}/json/pulse3d_${var.cluster_env}_iam_policy.json")
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
  name = "${var.cluster_name}-pulse3d-pods-iam-role01"

  assume_role_policy = data.aws_iam_policy_document.pulse3d_pods.json
}

resource "aws_iam_role_policy" "apiv2_pod_iam_role_policy" {
  name = "${var.cluster_name}-apiv2-pods-iam-role01"
  role = aws_iam_role.apiv2_pods.id

  policy = file("${path.module}/json/apiv2_${var.cluster_env}_iam_policy.json")
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
  name = "${var.cluster_name}-apiv2-pods-iam-role01"

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
  name = "${var.cluster_name}-loki-pods-iam-role01"

  assume_role_policy = data.aws_iam_policy_document.loki_pods.json
}
resource "aws_iam_role_policy" "loki_pod_iam_role_policy" {
  name = "${var.cluster_name}-loki-pods-iam-role01"
  role = aws_iam_role.loki_pods.id

  policy = file("${path.module}/json/loki_${var.cluster_env}_iam_policy.json")
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
  name = "${var.cluster_name}-operators-iam-role01"

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
  cluster_name    = "test-updated"
  cluster_version = "1.27"
  subnet_ids      = var.private_subnets

  tags   = var.cluster_tags
  vpc_id = var.vpc_id

  aws_auth_accounts              = var.cluster_accounts
  aws_auth_users                 = var.cluster_users
  manage_aws_auth_configmap      = true
  cluster_endpoint_public_access = true
  custom_oidc_thumbprints        = [data.external.thumbprint.result.thumbprint]
  # create                         = false

  eks_managed_node_groups = var.node_groups
}

data "aws_iam_policy" "ebs_csi_policy" {
  arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
}

module "irsa-ebs-csi" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-assumable-role-with-oidc"
  version = "4.7.0"

  create_role                   = true
  role_name                     = "AmazonEKSTFEBSCSIRole-${module.eks.cluster_name}"
  provider_url                  = replace(module.eks.cluster_oidc_issuer_url, "https://", "")
  role_policy_arns              = [data.aws_iam_policy.ebs_csi_policy.arn]
  oidc_fully_qualified_subjects = ["system:serviceaccount:kube-system:ebs-csi-controller-sa"]
}

resource "aws_eks_addon" "ebs-csi" {
  cluster_name             = module.eks.cluster_name
  addon_name               = "aws-ebs-csi-driver"
  addon_version            = "v1.20.0-eksbuild.1"
  service_account_role_arn = module.irsa-ebs-csi.iam_role_arn
  tags = {
    "eks_addon" = "ebs-csi"
    "terraform" = "true"
  }
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
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}
