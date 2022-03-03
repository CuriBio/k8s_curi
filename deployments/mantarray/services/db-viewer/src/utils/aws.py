import boto3
import json


def get_db_secrets():
    ssm_client = boto3.client("secretsmanager", region_name="us-east-2")

    # db creds
    creds_secret = ssm_client.get_secret_value(SecretId="test_aurora_postgresql")
    secrets_dict = json.loads(creds_secret["SecretString"])
    # db endpoint
    endpoint_secret = ssm_client.get_secret_value(SecretId="mantarray_db_endpoint")
    secrets_dict.update(json.loads(endpoint_secret["SecretString"]))

    # change key 'username' to 'user' so it matches accepted kwargs
    secrets_dict["user"] = secrets_dict.pop("username")

    return secrets_dict
