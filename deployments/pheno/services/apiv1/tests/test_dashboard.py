import asyncpg
import json
import unittest
import pytest
import sys
import os

from unittest.mock import MagicMock
from .conftest import client

sys.path.insert(0, '/Users/lucipak/Documents/work/CuriBio/k8s_curi/deployments/pheno/services/apiv1/src')
from src.lib import *
from src.lib.db import Database
from src.endpoints  import *
from src.main import app
from src import main



def test_usage_route(mocker, client):
    # client, cur = client

    response = client.get("/usage/1?month=2&year=2022")
    assert response.content == "hi"

