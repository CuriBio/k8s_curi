import json
import os
import sys
from unittest.mock import MagicMock


os.environ["JWT_SECRET_KEY"] = "1234"

# minimal mocking required to ensure that test collection won't fail and no connections to cloud need to be made
for mod_to_mock in ("psycopg2", "psycopg2.extras", "psycopg2.pool", "boto3"):
    sys.modules[mod_to_mock] = MagicMock()

# add auth from core lib
sys.path.append(os.path.join(os.getcwd(), *([os.pardir] * 4), "core", "lib", "auth"))


def get_secret_value_se(SecretId):
    mock_secret_dict = dict()
    if SecretId == "test_aurora_postgresql":
        mock_secret_dict["SecretString"] = json.dumps(
            {"reader_endpoint": "reader_endpoint", "writer_endpoint": "writer_endpoint"}
        )
    elif SecretId == "mantarray_db_endpoint":
        mock_secret_dict["SecretString"] = json.dumps({"username": "user"})
    else:
        raise ValueError(SecretId)
    return mock_secret_dict


sys.modules["boto3"].client.return_value.get_secret_value.side_effect = get_secret_value_se


# allow main to find utils
from src import utils

sys.modules["utils"] = utils
