from fastapi.testclient import TestClient
import json
import pytest
from random import choice, randint

from src import main
from src.utils.db import CONNECTION_POOLS as mocked_connection_pools

test_client = TestClient(main.app)


@pytest.fixture(autouse=True)
def reset_db_conn_mocks_after_each_test():
    yield
    for mock in mocked_connection_pools.values():
        mock.reset_mock()


def test_default_route(mocker):
    mocked_reader_cursor = mocked_connection_pools["reader"].getconn().cursor()

    expected_db_entries = [
        {"serial_number": "123", "hw_version": "1.2.3"},
        {"serial_number": "444", "hw_version": "0.0.0"},
    ]
    # return a list of dicts here, but cursor will actually return an object with these keys/vals as attr names/vals
    mocked_reader_cursor.fetchall.return_value = expected_db_entries

    expected_template_response = {"key": "val"}
    mocked_template_response = mocker.patch.object(
        main.templates, "TemplateResponse", autospec=True, return_value=json.dumps(expected_template_response)
    )

    response = test_client.get("/")
    assert response.status_code == 200
    assert json.loads(response.json()) == expected_template_response

    mocked_reader_cursor.execute.assert_called_once_with("SELECT * FROM MAUnits")
    mocked_reader_cursor.fetchall.assert_called_once_with()
    mocked_template_response.assert_called_once_with(
        "table.html", {"request": mocker.ANY, "units": expected_db_entries}
    )


def test_firmware_latest(mocker):
    mocked_reader_cursor = mocked_connection_pools["reader"].getconn().cursor()

    expected_latest_fw_version = "1.1.1"
    mocked_get_latest_firmware_version = mocker.patch.object(
        main, "get_latest_firmware_version", autospec=True, return_value=expected_latest_fw_version
    )

    test_serial_number = "MA2022001000"
    response = test_client.get(f"/firmware_latest?serial_number={test_serial_number}")
    assert response.status_code == 200
    assert response.json() == {"latest_versions": "1.1.1"}

    mocked_reader_cursor.execute.assert_called_once_with(
        f"SELECT hw_version FROM MAUnits WHERE serial_number = '$1'", test_serial_number
    )
    mocked_reader_cursor.fetchone.assert_called_once_with()
    mocked_get_latest_firmware_version.assert_called_once_with(mocked_reader_cursor.fetchone()[0])


def test_firmware_download(mocker):
    expected_url = "url"
    mocked_get_url = mocker.patch.object(main, "get_download_url", autospec=True, return_value=expected_url)

    test_firmware_version = "1.1.1"
    test_firmware_type = choice(["main", "channel"])
    response = test_client.get(
        f"/firmware_download?firmware_version={test_firmware_version}&firmware_type={test_firmware_type}"
    )
    assert response.status_code == 200
    assert response.json() == {"presigned_url": expected_url}

    mocked_get_url.assert_called_once_with(test_firmware_version, test_firmware_type)


@pytest.mark.parametrize("bad_param_type", ["firmware_version", "firmware_type"])
def test_firmware_download__params(bad_param_type):
    test_params = {
        "firmware_version": f"{randint(0,1000)}.{randint(0,1000)}.{randint(0,1000)}",
        "firmware_type": choice(["main", "channel"]),
    }
    test_params[bad_param_type] = "bad"

    response = test_client.get(f"/firmware_download", params=test_params)
    assert response.status_code == 422
