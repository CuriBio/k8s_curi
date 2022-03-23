import sys
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from asynctest import CoroutineMock

ROOT_DIR = os.path.dirname(os.path.abspath("src"))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from main import app
from lib.db import Database
from lib.db import get_cur


@pytest.fixture
def mock_cursor():
    mocked_get_cur = AsyncMock()
    mocked_get_cur.fetchrow = CoroutineMock()
    mocked_get_cur.fetchval = CoroutineMock()
    mocked_get_cur.execute = CoroutineMock()
    mocked_get_cur.fetch = CoroutineMock()
    yield mocked_get_cur


@pytest.fixture
def client(mocker, mock_cursor):
    # mock db class
    mocker.patch.object(Database, "create_pool", autospec=True)
    mocker.patch.object(Database, "close", autospec=True)
    # override cursor dependency
    app.dependency_overrides[get_cur] = lambda: mock_cursor

    with TestClient(app) as client:
        yield client
