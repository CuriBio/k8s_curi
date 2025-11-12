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

# read in env file
if [[ -z "$2" ]]; then
    echo "ERROR: path to env file must be provided"
    exit 1
fi
source $2

# create advanced-analysis secrets.yaml
kc create secret generic xxx -n advanced-analysis --dry-run=client \
    --from-literal=curibio_advanced_analysis=$ADVANCED_ANALYSIS_PASS -o yaml \
    | kubeseal --kubeconfig=$3 --format yaml --merge-into ./deployments/advanced-analysis/manifests/overlays/$1/curibio-advanced-analysis-creds.yaml
