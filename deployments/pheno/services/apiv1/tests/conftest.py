import sys
import os
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.abspath("src"))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from main import app
from lib.db import Database


@pytest.fixture
def client(mocker):
    # mock db class
    mocker.patch.object(Database, "create_pool")
    mocker.patch.object(Database, "close")
    mocker.patch.object(Database, "get_cur")

    with TestClient(app) as c:
        yield c
