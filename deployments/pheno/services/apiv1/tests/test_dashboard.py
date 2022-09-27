from src.lib import *
from src.lib.models import *


def test_usage_route__returns_correct_query_count(client, mock_cursor):
    mock_cursor.fetchrow.return_value = {"total_processingtime": 80}
    client.get("/usage/1?month=2&year=2022")
    assert mock_cursor.fetchrow.await_count == 2


def test_usage_route__will_error_if_missing_params(client, mock_cursor):
    response = client.get("/usage/1")

    assert "Request validation error" in response.json()["detail"]
    assert response.status_code == 400
    mock_cursor.fetchrow.assert_not_awaited()
