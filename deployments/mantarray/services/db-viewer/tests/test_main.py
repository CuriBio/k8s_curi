from fastapi.testclient import TestClient
import json
from src import main
from src.utils.db import CONNECTION_POOLS

test_client = TestClient(main.app)


def test_default_route(mocker):
    expected_db_entries = [
        {"serial_number": "123", "hw_version": "1.2.3"},
        {"serial_number": "444", "hw_version": "0.0.0"},
    ]

    reader_cursor = CONNECTION_POOLS["reader"].getconn().cursor()
    # return a list of dicts here, but cursor will actually return an object with these keys/vals as attr names/vals
    reader_cursor.fetchall.return_value = expected_db_entries

    expected_template_response = {"key": "val"}
    mocked_template_response = mocker.patch.object(
        main.templates, "TemplateResponse", autospec=True, return_value=json.dumps(expected_template_response)
    )

    response = test_client.get("/")
    assert response.status_code == 200
    assert json.loads(response.json()) == expected_template_response

    reader_cursor.execute.assert_called_once_with("SELECT * FROM MAUnits;")
    reader_cursor.fetchall.assert_called_once_with()
    mocked_template_response.assert_called_once_with(
        "table.html", {"request": mocker.ANY, "units": expected_db_entries}
    )
