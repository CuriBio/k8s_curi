import asyncpg
import json
import unittest
import pytest
import sys

from unittest.mock import MagicMock
from fastapi.testclient import TestClient

sys.path.insert(0, '/Users/lucipak/Documents/work/CuriBio/k8s_curi/deployments/pheno/services/apiv1/src')
from src.lib import *
from src.lib.db import Database
from src.endpoints  import *
from src.main import app
from src import main

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# @pytest.mark.anyio
def test_default_route(mocker, client):
    response = client.get("/")
    assert json.loads(response.content) == "hi"

