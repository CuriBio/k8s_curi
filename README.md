# Init cluster (only need this if the cluster isn't already setup)

terraform init -backend-config=backend/test_env_config.yaml

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
test workflow
