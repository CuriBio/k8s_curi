import uuid
from fastapi.testclient import TestClient
import json
import pytest
from random import choice, randint

from auth import create_token
from src import main

test_client = TestClient(main.app)


def random_semver():
    return f"{randint(0,1000)}.{randint(0,1000)}.{randint(0,1000)}"


def random_firmware_type():
    return choice(["main", "channel"])


@pytest.fixture(scope="function", name="auth_token")
def fixture_auth_token():
    yield create_token(scope=main.AUTH.scope, userid=uuid.uuid4()).access_token


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


def test_firmware_latest__success(mocker):
    mocked_reader_cursor = mocked_connection_pools["reader"].getconn().cursor()

    expected_latest_fw_version = random_semver()
    mocked_get_latest_firmware_version = mocker.patch.object(
        main, "resolve_versions", autospec=True, return_value=expected_latest_fw_version
    )

    test_serial_number = "MA2022001000"
    response = test_client.get(f"/firmware_latest", params={"serial_number": test_serial_number})
    assert response.status_code == 200
    assert response.json() == {"latest_versions": expected_latest_fw_version}

    mocked_reader_cursor.execute.assert_called_once_with(
        f"SELECT hw_version FROM MAUnits WHERE serial_number = '$1'", test_serial_number
    )
    mocked_reader_cursor.fetchone.assert_called_once_with()
    mocked_get_latest_firmware_version.assert_called_once_with(mocked_reader_cursor.fetchone()[0])


def test_firmware_latest__serial_number_not_found(mocker):
    mocked_reader_cursor = mocked_connection_pools["reader"].getconn().cursor()
    mocked_reader_cursor.fetchone.side_effect = Exception()

    test_serial_number = "MA2022001000"
    response = test_client.get(f"/firmware_latest", params={"serial_number": test_serial_number})
    assert response.status_code == 404
    assert response.json() == {"message": f"Serial Number {test_serial_number} not found"}


def test_firmware_download__success(auth_token, mocker):
    expected_url = "url"
    mocked_get_url = mocker.patch.object(main, "get_download_url", autospec=True, return_value=expected_url)

    test_firmware_version = random_semver()
    test_firmware_type = random_firmware_type()
    response = test_client.get(
        f"/firmware_download",
        params={"firmware_version": test_firmware_version, "firmware_type": test_firmware_type},
        headers={f"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"presigned_url": expected_url}

    mocked_get_url.assert_called_once_with(test_firmware_version, test_firmware_type)


@pytest.mark.parametrize("bad_param_type", ["firmware_version", "firmware_type"])
def test_firmware_download__bad_query_params(auth_token, bad_param_type):
    test_params = {"firmware_version": random_semver(), "firmware_type": random_firmware_type()}
    # change one param to invalid value
    test_params[bad_param_type] = "bad"

    response = test_client.get(
        f"/firmware_download", params=test_params, headers={f"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 422


def test_firmware_download__no_auth_token_given():
    test_params = {"firmware_version": random_semver(), "firmware_type": random_firmware_type()}
    response = test_client.get(f"/firmware_download", params=test_params)
    assert response.status_code == 403


def test_firmware_download__bad_auth_token_given():
    test_params = {"firmware_version": random_semver(), "firmware_type": random_firmware_type()}
    response = test_client.get(
        f"/firmware_download", params=test_params, headers={f"Authorization": f"Bearer bad.auth.token"}
    )
    assert response.status_code == 401
