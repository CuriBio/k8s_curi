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

data "aws_region" "current" {}
data "external" "thumbprint" {
  program = ["/bin/sh", "${path.module}/external/thumbprint.sh", data.aws_region.current.name]
}

resource "aws_iam_openid_connect_provider" "default" {
  url = module.eks.cluster_oidc_issuer_url
  client_id_list  = ["sts.amazonaws.com" ]
  thumbprint_list = [data.external.thumbprint.result.thumbprint]
}

# module "mantarray_namespace_policy" {
#   source = "./modules/service_account_namespace"

#   namespace = "mantarray"
#   policy_file_name = "mantarray_namespace_iam_policy.json"
#   iam_role_name = "MantarrayPodIAMPolicy"
#   iam_role_policy_name = "mantarray-pods-iam-role01"

#   namespace_annotations = {
#     name = "mantarray namespace"
#   }

#   openid_connect_provider = aws_iam_openid_connect_provider.default
# }

# module "temp_namespace_policy" {
#   source = "./modules/service_account_namespace"

#   namespace = "temp"
#   policy_file_name = "temp_namespace_iam_policy.json"
#   iam_role_name = "TempPodIAMPolicy"
#   iam_role_policy_name = "temp-pods-iam-role01"

#   namespace_annotations = {
#     name = "temp namespace"
#   }

#   openid_connect_provider = aws_iam_openid_connect_provider.default
# }
#
# module "argo_namespace_policy" {
#   source = "./modules/service_account_namespace"

#   name = "argo"
#   namespace = "argo"
#   policy_file_name = "argo_namespace_iam_policy.json"
#   iam_role_name = "ArgoPodIAMPolicy"
#   iam_role_policy_name = "argo-pods-iam-role01"

#   namespace_annotations = {
#     name = "argo namespace"
#   }

#   openid_connect_provider = aws_iam_openid_connect_provider.default
# }

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
    example = {
      desired_capacity = 5
      max_capacity     = 10
      min_capacity     = 1

      instance_types = ["t3a.medium"]

      k8s_labels = {
        Environment = "prod"
      }
      additional_tags = {
        ExtraTag = "example"
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
