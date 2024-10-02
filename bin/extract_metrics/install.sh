# NOTE need to set AWS_PROFILE before running this
export AWS_ACCOUNT_ID=725604423866
export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token --domain curibio --domain-owner $AWS_ACCOUNT_ID --query authorizationToken --output text)
pip install -r requirements.txt --extra-index-url=https://aws:$CODEARTIFACT_AUTH_TOKEN@curibio-$AWS_ACCOUNT_ID.d.codeartifact.us-east-2.amazonaws.com/pypi/pulse3d/simple/
pip install -e ../../core/lib/utils
