import json
import sys
from unittest.mock import MagicMock

# minimal mocking required to ensure that test collection won't fail and no connections to cloud need to be made
for mod_to_mock in ("psycopg2", "psycopg2.extras", "psycopg2.pool", "boto3"):
    sys.modules[mod_to_mock] = MagicMock()


def get_secret_value_se(SecretId):
    mock_secret_dict = dict()
    if SecretId == "test_aurora_postgresql":
        mock_secret_dict["SecretString"] = json.dumps(
            {"reader_endpoint": "reader_endpoint", "writer_endpoint": "writer_endpoint"}
        )
    else:
        mock_secret_dict["SecretString"] = json.dumps({"username": "user"})
    return mock_secret_dict


sys.modules["boto3"].client.return_value.get_secret_value.side_effect = get_secret_value_se
