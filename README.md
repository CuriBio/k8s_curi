> New developer? Start with [DEV_SETUP.md](DEV_SETUP.md).

# Terraform

This section is for developers who haven't used Terraform before.

## What Terraform is

Terraform is a tool that creates and changes cloud infrastructure from code. Instead of clicking through the AWS console, you describe what should exist in `.tf` files, and Terraform makes AWS match that description. In this repo, Terraform manages each cluster's AWS resources: the EKS cluster and its node groups, the network (VPC), IAM roles, S3 buckets, EKS add-ons, and the list of users who can access the cluster.

It doesn't deploy the apps and services. Those are Kubernetes manifests under `deployments/`.

## The pieces

| Term | What it means here |
|---|---|
| Configuration | The `.tf` files in `cluster/terraform/`. They describe what should exist. All three clusters share them |
| Variables file | `cluster/terraform/<cluster>_env.tfvars`. The values that differ per cluster, such as the cluster name, `cluster_users` and `cluster_version` |
| State | Terraform's record of what it created last time. Each cluster's state is a file in that account's S3 bucket (`curi-eks-<cluster>-cluster-tf-state`), not in the repo |
| Backend config | `cluster/terraform/backend/<cluster>_env_config.tfvars`. Tells Terraform which S3 bucket holds the state |
| Provider | A plugin Terraform uses to talk to a service (AWS, Kubernetes). `terraform init` downloads them |
| Module | A reusable bundle of configuration. `cluster/terraform/k8s/` is ours; others are downloaded from the public registry |

## The three commands

| Command | What it does | Changes anything? |
|---|---|---|
| `terraform init` | Downloads providers and modules, and connects to the cluster's state in S3 | Only local files (`.terraform/`, which is gitignored) |
| `terraform plan` | Compares the configuration with what really exists and prints what it would change | No. It only reads |
| `terraform apply` | Shows the same plan, asks you to type `yes`, then makes the changes | **Yes** |

Always read a plan before applying it.

## Run a plan

You need Terraform 1.5.2, an AWS profile for the cluster's account, and Kubernetes access to the cluster (see [DEV_SETUP.md](DEV_SETUP.md)). This example uses modl:

```bash
cd cluster/terraform
export AWS_PROFILE=curi_modl AWS_REGION=us-east-2

terraform init -reconfigure -backend-config=backend/modl_env_config.tfvars
terraform plan -var-file=modl_env.tfvars
```

- Set both variables. `AWS_PROFILE` picks the AWS account, and `AWS_REGION` is needed when Terraform signs in to the cluster.
- The backend config and the `-var-file` must be for the **same cluster**. Mixing them (for example modl's state with `prod_env.tfvars`) makes Terraform plan to rebuild one cluster to look like another.
- Use `-reconfigure` whenever you switch clusters, so `init` doesn't reuse the previous cluster's state.

## Read the plan

A plan prints a lot of `Refreshing state...` and `Reading...` lines first. That's Terraform checking each resource in AWS; you can skip them. The parts that matter come after:

**"Objects have changed outside of Terraform"** lists things that someone changed by hand since the last apply, for example a Kubernetes version upgrade done in the console:

```
  # module.eks_cluster_v2.module.eks.aws_eks_cluster.this[0] has changed
      ~ version                   = "1.33" -> "1.36"
```

**"Terraform will perform the following actions"** is what an apply would do. Each resource has a symbol:

| Symbol | Meaning |
|---|---|
| `+` | Create |
| `~` | Update in place |
| `-` | Destroy |
| `-/+` or `+/-` | Destroy and re-create (a replacement) |

```
  # module.eks_cluster_v2.aws_eks_addon.kube_proxy will be updated in-place
  ~ resource "aws_eks_addon" "kube_proxy" {
      ~ addon_version               = "v1.33.5-eksbuild.2" -> "v1.36.0-eksbuild.65"
```

The last line is the summary:

```
Plan: 1 to add, 2 to change, 1 to destroy.
```

Check that every item in the plan is something you meant to change. Be most careful with anything marked destroy or replace: for a cluster, node group, database or bucket, that means downtime or data loss. If the plan shows changes you didn't make, stop and ask before applying. It usually means the cluster was changed by hand, or your branch is out of date.

`No changes. Your infrastructure matches the configuration.` means there's nothing to apply.

## How changes get applied

Normally you don't run `terraform apply` yourself. CI runs it when a PR that changes `cluster/terraform` is merged:

| Cluster | Applied when |
|---|---|
| `prod` | A PR merges into `main`. It runs with `-auto-approve`, so there's no confirmation step |
| `modl` | A PR merges into `modl-qc` |
| `test` | Never automatically. Someone runs the apply by hand |

To apply by hand, use the same commands as the plan, with `apply` in place of `plan`:

```bash
terraform apply -var-file=<cluster>_env.tfvars
```

Terraform prints the plan and waits for you to type `yes`. An apply covers the whole cluster's configuration, not just your change.

## Kubernetes version upgrades

Kubernetes version upgrades are done in the AWS console, one minor version at a time, not through Terraform. After an upgrade, set `cluster_version` and the add-on versions in that cluster's `<cluster>_env.tfvars` to match. If you don't, the next apply fails, because Terraform tries to put the old version back and EKS can't downgrade.

# Init cluster (only need this if the cluster isn't already setup)

terraform init -backend-config=backend/test_env_config.tfvars

# Create cluster (only need this if the cluster isn't already setup)

terraform apply -backend-config=backend/\<config\>.tfvars

# Useful kubectl commands

list all commands

> kubectl --help

get specific command help

> kubectl \<command\> \<param\> --help

get running [deployments|services|pods]

> kubectl get pods

delete resources

> kubectl delete \<resource type\> \<name prefix\>

get logs of running pod

> kubectl get logs \<pod name\>

port forward traffic to cluster service

> kubectl port-forward svc/\<service name\> 8080:443

show details of a resource (for example the ingress controllers)

> kubectl describe ingress

create and run a container (for quick testing)

> kubectl run -i --tty \<name\> --image \<image\>

> kubectl run -i --tty temp-pod --image ubuntu:18.04

# Create new service in existing deployment

> python ccc.py \<repo path\> deployment new --name=sample
>
> python ccc.py \<repo path\> service add --deployment=sample --name=test3

> cd <repo path>/deployemnts/sample/services/test3/terraform

> terraformm init -backend-config=backends/test_env_config.tfvars

> terraform apply

- make updates to \<repo path\>/deployments/sample/services/test3/Dockerfile as needed
- make updates to \<repo path\>/deployments/sample/services/test3/Makefile as needed
- make updates to \<repo path\>/deployments/sample/manifests/sample-dep.yaml as needed
- make updates to \<repo path\>/deployments/sample/manifests/test3-svc.yaml as needed

> cd \<repo path\>/deployments/sample/services/test3

- login needs to have your AWS_PROFILE set
- use build if you're building on an x86 machine, buildx if you're on some other arch
  > make login build tag push

> cd \<repo path\>/deployments/sample

> kubectl apply -f ./manifests

- verify your sevice is started
  > kubect get svc
