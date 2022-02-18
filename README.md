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
