import pytest
import sys


sys.path.insert(0, "/Users/lucipak/Documents/work/CuriBio/k8s_curi/deployments/pheno/services/apiv1/src")
from src.lib import *
from src.endpoints import *


@pytest.mark.asyncio
def test_usage_route(mocker, client, mock_cursor):
    mock_cursor.fetchrow.return_value = {"test": 2}

    response = client.get("/usage/1?month=2&year=2022")

    # print(dir(cur.fetchrow))
    mock_cursor.fetchrow.assert_awaited()
    assert response.content == "hi"
