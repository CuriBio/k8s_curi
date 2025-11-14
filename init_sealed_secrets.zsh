# Set up kubectl alias. This assumes that the aliases for each cluster are already set in ~/.zshrc
source ~/.zshrc
alias=""
if [[ $1 =~ "test" ]]; then
    alias="ktest"
elif [[ $1 =~ "modl" ]]; then
    alias="kmodl"
elif [[ $1 =~ "modl" ]]; then
    alias="kprod"
else
    echo "ERROR: cluster must be test/modl/prod"
    exit 1
fi
kc () {
    eval "$alias" $@
}

# Read in env file
if [[ -z "$2" ]]; then
    echo "ERROR: path to env file must be provided"
    exit 1
fi
source $2

# Create secrets
if [[ -z "$2" ]]; then
    echo "ERROR: path to kube config file must be provided"
    exit 1
fi

# advanced analysis deployment
# kc create secret generic xxx -n advanced-analysis --dry-run=client \
#     --from-literal=curibio_advanced_analysis=$ADVANCED_ANALYSIS_PASS \
#     -o yaml \
#     | kubeseal --kubeconfig=$3 --format yaml --merge-into ./deployments/advanced-analysis/manifests/overlays/$1/curibio-advanced-analysis-creds.yaml
#
# kc create secret generic xxx -n advanced-analysis --dry-run=client \
#     --from-literal=curibio-email=$CURIBIO_EMAIL \
#     --from-literal=curibio-email-password=$CURIBIO_EMAIL_PASSWORD \
#     -o yaml \
#     | kubeseal --kubeconfig=$3 --format yaml --merge-into ./deployments/advanced-analysis/manifests/overlays/$1/curibio-email-creds.yaml
#
# kc create secret generic xxx -n advanced-analysis --dry-run=client \
#     --from-literal=jwt-secret=$JWT_SECRET \
#     -o yaml \
#     | kubeseal --kubeconfig=$3 --format yaml --merge-into ./deployments/advanced-analysis/manifests/overlays/$1/curibio-jwt-secret.yaml

# apiv2 deployment
# kc create secret generic xxx -n apiv2 --dry-run=client \
#     --from-literal=curibio-email=$CURIBIO_EMAIL \
#     --from-literal=curibio-email-password=$CURIBIO_EMAIL_PASSWORD \
#     -o yaml \
#     | kubeseal --kubeconfig=$3 --format yaml --merge-into ./deployments/apiv2/manifests/overlays/$1/curibio-email-creds.yaml
#
# kc create secret generic xxx -n apiv2 --dry-run=client \
#     --from-literal=curibio_event_broker=$EVENT_BROKER_PASS \
#     -o yaml \
#     | kubeseal --kubeconfig=$3 --format yaml --merge-into ./deployments/apiv2/manifests/overlays/$1/curibio-event-broker-creds.yaml
#
# kc create secret generic xxx -n apiv2 --dry-run=client \
#     --from-literal=jwt-secret=$JWT_SECRET \
#     -o yaml \
#     | kubeseal --kubeconfig=$3 --format yaml --merge-into ./deployments/apiv2/manifests/overlays/$1/curibio-jwt-secret.yaml
#
# kc create secret generic xxx -n apiv2 --dry-run=client \
#     --from-literal=curibio_mantarray=$MANTARRAY_USER_PASS \
#     --from-literal=curibio_mantarray_ro=$MANTARRAY_USER_PASS_RO\
#     -o yaml \
#     | kubeseal --kubeconfig=$3 --format yaml --merge-into ./deployments/apiv2/manifests/overlays/$1/curibio-mantarray-creds.yaml
#
# kc create secret generic xxx -n apiv2 --dry-run=client \
#     --from-literal=curibio_users=$TABLE_USER_PASS \
#     --from-literal=curibio_users_ro=$TABLE_USER_PASS_RO \
#     -o yaml \
#     | kubeseal --kubeconfig=$3 --format yaml --merge-into ./deployments/apiv2/manifests/overlays/$1/curibio-users-creds.yaml

# pulse3d deployment
kc create secret generic xxx -n pulse3d --dry-run=client \
    --from-literal=curibio-email=$CURIBIO_EMAIL \
    --from-literal=curibio-email-password=$CURIBIO_EMAIL_PASSWORD \
    -o yaml \
    | kubeseal --kubeconfig=$3 --format yaml --merge-into ./deployments/pulse3d/manifests/overlays/$1/curibio-email-creds.yaml

kc create secret generic xxx -n pulse3d --dry-run=client \
    --from-literal=curibio_jobs=$JOBS_USER_PASS \
    --from-literal=curibio_jobs_ro=$JOBS_USER_PASS_RO \
    -o yaml \
    | kubeseal --kubeconfig=$3 --format yaml --merge-into ./deployments/pulse3d/manifests/overlays/$1/curibio-jobs-creds.yaml

kc create secret generic xxx -n pulse3d --dry-run=client \
    --from-literal=jwt-secret=$JWT_SECRET \
    -o yaml \
    | kubeseal --kubeconfig=$3 --format yaml --merge-into ./deployments/pulse3d/manifests/overlays/$1/curibio-jwt-secret.yaml
