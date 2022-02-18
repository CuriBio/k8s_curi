import boto3
import json
from botocore.exceptions import ClientError


def get_ssm_secrets():
    # Get db credentials to connect
    creds_secret_name = "db-creds"

    # Create a ssm client
    ssm_client = boto3.client("secretsmanager")

    try:
        get_creds_secret_value_response = ssm_client.get_secret_value(SecretId=creds_secret_name)
    except ClientError as e:
        raise ClientError(f"error retrieving aws secrets: {e}")
    else:
        creds_secret = get_creds_secret_value_response["SecretString"]
        parsed_creds_secret = json.loads(creds_secret)
        return parsed_creds_secret["username"], parsed_creds_secret["password"]
