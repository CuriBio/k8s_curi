import json
import os
import sys
from unittest.mock import MagicMock


JWT_SECRET_KEY = "1234"
POSTGRES_DB = "test_db"
POSTGRES_USER = "test_pg_user"
POSTGRES_PASSWORD = "test_pw"

os.environ["JWT_SECRET_KEY"] = JWT_SECRET_KEY
os.environ["POSTGRES_DB"] = "test_db"
os.environ["POSTGRES_USER"] = "test_pg_user"
os.environ["POSTGRES_PASSWORD"] = "test_pw"

# minimal mocking required to ensure that test collection won't fail and no connections to cloud need to be made
for mod_to_mock in ("boto3",):  # "psycopg2", "psycopg2.extras", "psycopg2.pool",
    sys.modules[mod_to_mock] = MagicMock()

# add auth from core lib
# sys.path.append(os.path.join(os.getcwd(), *([os.pardir] * 4), "core", "lib", "auth"))


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


# import core and add to sys.modules so that main.py can find it, not sure why it can't otherwise
from src import core

sys.modules["core"] = core
