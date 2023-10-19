import json
import os
import sys
from unittest.mock import MagicMock

CLUSTER_NAME = "test"
JWT_SECRET_KEY = "1234"
POSTGRES_DB = "test_db"
POSTGRES_USER = "test_pg_user"
POSTGRES_PASSWORD = "test_pw"

os.environ["CLUSTER_NAME"] = CLUSTER_NAME
os.environ["JWT_SECRET_KEY"] = JWT_SECRET_KEY
os.environ["POSTGRES_DB"] = POSTGRES_DB
os.environ["POSTGRES_USER"] = POSTGRES_USER
os.environ["POSTGRES_PASSWORD"] = POSTGRES_PASSWORD


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
from src import models

sys.modules["core"] = core
sys.modules["models"] = models
