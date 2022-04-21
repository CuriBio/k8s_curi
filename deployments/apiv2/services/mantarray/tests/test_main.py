from re import I
import uuid
from fastapi.testclient import TestClient
import json
import pytest
import pytest_asyncio
from random import choice, randint

import asyncpg
from auth import create_token
from utils.db import AsyncpgPoolDep
from src import main

test_client = TestClient(main.app)


def random_semver():
    return f"{randint(0,1000)}.{randint(0,1000)}.{randint(0,1000)}"


def random_firmware_type():
    return choice(["main", "channel"])


@pytest.fixture(scope="function", name="auth_token")
def fixture_auth_token():
    yield create_token(scope=main.AUTH.scope, userid=uuid.uuid4()).access_token


@pytest.fixture(scope="function", name="mocked_asyncpg_con", autouse=True)
async def fixture_mocked_asyncpg_con(mocker):
    mocked_asyncpg_pool = mocker.patch.object(main, "asyncpg_pool", autospec=True)

    mocked_asyncpg_pool_coroutine = mocker.AsyncMock()
    mocked_asyncpg_pool_coroutine.return_value = mocker.MagicMock()
    mocked_asyncpg_pool.return_value = mocked_asyncpg_pool_coroutine()

    mocked_asyncpg_con = await mocked_asyncpg_pool_coroutine.return_value.acquire().__aenter__()
    yield mocked_asyncpg_con


def test_default_route(mocker, mocked_asyncpg_con):
    expected_db_entries = [
        {"serial_number": "123", "hw_version": "1.2.3"},
        {"serial_number": "444", "hw_version": "0.0.0"},
    ]
    # return a list of dicts here, but fetch will actually return a Record object with these keys/vals as attr names/vals
    mocked_asyncpg_con.fetch.return_value = expected_db_entries

    expected_template_response = {"key": "val"}
    mocked_template_response = mocker.patch.object(
        main.templates, "TemplateResponse", autospec=True, return_value=json.dumps(expected_template_response)
    )

    response = test_client.get("/")
    assert response.status_code == 200
    assert json.loads(response.json()) == expected_template_response

    mocked_asyncpg_con.fetch.assert_called_once_with("SELECT * FROM MAUnits")
    mocked_template_response.assert_called_once_with(
        "table.html", {"request": mocker.ANY, "units": expected_db_entries}
    )


def test_firmware_latest__success(mocked_asyncpg_con, mocker):
    expected_latest_fw_version = random_semver()
    mocked_get_latest_firmware_version = mocker.patch.object(
        main, "resolve_versions", autospec=True, return_value=expected_latest_fw_version
    )

    expected_hw_version = "2.2.2"
    mocked_asyncpg_con.fetchrow.return_value = {"hw_version": expected_hw_version}

    test_serial_number = "MA2022001000"
    response = test_client.get("/firmware_latest", params={"serial_number": test_serial_number})
    assert response.status_code == 200
    assert response.json() == {"latest_versions": expected_latest_fw_version}

    mocked_asyncpg_con.fetchrow.assert_called_once_with(
        "SELECT hw_version FROM MAUnits WHERE serial_number = $1", test_serial_number
    )
    mocked_get_latest_firmware_version.assert_called_once_with(expected_hw_version)


def test_firmware_latest__serial_number_not_found_in_db(mocked_asyncpg_con):
    mocked_asyncpg_con.fetchrow.side_effect = Exception()

    test_serial_number = "MA2022001000"
    response = test_client.get("/firmware_latest", params={"serial_number": test_serial_number})
    assert response.status_code == 404
    assert response.json() == {"message": f"Serial Number {test_serial_number} not found"}


def test_firmware_download__success(auth_token, mocker):
    expected_url = "url"
    mocked_get_url = mocker.patch.object(main, "get_download_url", autospec=True, return_value=expected_url)

    test_firmware_version = random_semver()
    test_firmware_type = random_firmware_type()
    response = test_client.get(
        "/firmware_download",
        params={"firmware_version": test_firmware_version, "firmware_type": test_firmware_type},
        headers={"Authorization": f"Bearer {auth_token}"},
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
        "/firmware_download", params=test_params, headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 422


def test_firmware_download__no_auth_token_given():
    test_params = {"firmware_version": random_semver(), "firmware_type": random_firmware_type()}
    response = test_client.get("/firmware_download", params=test_params)
    assert response.status_code == 403


def test_firmware_download__bad_auth_token_given():
    test_params = {"firmware_version": random_semver(), "firmware_type": random_firmware_type()}
    response = test_client.get(
        "/firmware_download", params=test_params, headers={"Authorization": "Bearer bad.auth.token"}
    )
    assert response.status_code == 401
