# Init cluster
terraform init -backend-config=backend/test_env_config.yaml

# Create cluster
terraform apply
