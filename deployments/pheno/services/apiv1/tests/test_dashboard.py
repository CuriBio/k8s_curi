import pytest
import sys
import os
from fastapi import HTTPException

ROOT_DIR = os.path.dirname(os.path.abspath("src"))
sys.path.insert(0, ROOT_DIR)
from src.lib import *
from src.lib.models import *


def test_usage_route__returns_correct_query_count(client, mock_cursor):
    mock_cursor.fetchrow.return_value = {
        "trainings": 1,
    }
    client.get("/usage/1?month=2&year=2022")
    assert mock_cursor.fetchrow.await_count == 2


def test_usage_route__will_error_if_missing_params(client, mock_cursor):
    with pytest.raises(HTTPException) as error:  # default fastapi error with missing params
        client.get("/usage/1")

    assert "field required" in error.value.detail
    mock_cursor.fetchrow.assert_not_awaited()
