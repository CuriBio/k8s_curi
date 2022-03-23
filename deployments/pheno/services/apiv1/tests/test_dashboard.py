import pytest
import sys


sys.path.insert(0, "/Users/lucipak/Documents/work/CuriBio/k8s_curi/deployments/pheno/services/apiv1/src")
from src.lib import *
from src.lib.models import *


def test_usage_route__returns_correct_query_count(client, mock_cursor):
    mock_cursor.fetchrow.return_value = {
        "trainings": 1,
    }
    client.get("/usage/1?month=2&year=2022")

    assert mock_cursor.fetchrow.await_count == 2

def test_usage_route__returns_correct_response_model(client, mock_cursor):
    mock_cursor.fetchrow.return_value = {
        "trainings": 1,
    }
    client.get("/usage/1?month=2&year=2022")

    assert mock_cursor.fetchrow.await_count == 2