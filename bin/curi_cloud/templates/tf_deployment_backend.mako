bucket               = "curi-eks-${env}-cluster-tf-state"
key                  = "${env}/${deployment}/terraform.tfstate"
region               = "us-east-2"
dynamodb_table       = ""
workspace_key_prefix = "env"
