import uuid
from fastapi.testclient import TestClient
import pytest
from random import choice, randint

from auth import create_token
from src import main
from src.models.models import FirmwareUploadResponse

test_client = TestClient(main.app)


def random_semver():
    return f"{randint(0,1000)}.{randint(0,1000)}.{randint(0,1000)}"


def random_firmware_type():
    return choice(["main", "channel"])


def random_software_type():
    return choice(["mantarray", "stingray"])


def get_token(*, scope):
    return create_token(
        userid=uuid.uuid4(), customer_id=uuid.uuid4(), scope=scope, account_type="user", refresh=False
    ).token


ROUTES_WITH_AUTH = (
    ("POST", "/serial-number"),
    ("DELETE", "/serial-number/test_serial_number"),
    ("GET", "/firmware/info"),
    ("GET", f"/firmware/{random_firmware_type()}/{random_semver()}"),
    ("POST", f"/firmware/{random_firmware_type()}/{random_semver()}"),
    ("PUT", f"/firmware/{random_firmware_type()}/{random_semver()}"),
    ("POST", f"/firmware/{random_software_type()}/{random_semver()}"),
)


@pytest.fixture(scope="function", name="mocked_asyncpg_con", autouse=True)
async def fixture_mocked_asyncpg_con(mocker):
    mocked_asyncpg_pool = mocker.patch.object(main, "asyncpg_pool", autospec=True)

    mocked_asyncpg_pool_coroutine = mocker.AsyncMock()
    mocked_asyncpg_pool_coroutine.return_value = mocker.MagicMock()
    mocked_asyncpg_pool.return_value = mocked_asyncpg_pool_coroutine()

    mocked_asyncpg_con = await mocked_asyncpg_pool_coroutine.return_value.acquire().__aenter__()
    yield mocked_asyncpg_con


@pytest.mark.parametrize("test_method,test_route", ROUTES_WITH_AUTH)
def test_routes_with_auth__no_access_token_given(test_method, test_route):
    assert getattr(test_client, test_method.lower())(test_route).status_code == 403


@pytest.mark.parametrize("test_method,test_route", ROUTES_WITH_AUTH)
def test_routes_with_auth__bad_access_token_given(test_method, test_route):
    response = getattr(test_client, test_method.lower())(
        test_route, headers={"Authorization": "Bearer bad.auth.token"}
    )
    assert response.status_code == 401


@pytest.mark.parametrize("test_method,test_route", ROUTES_WITH_AUTH)
def test_routes_with_auth__invalid_scope_given(test_method, test_route):
    access_token = get_token(scope=["bad"])

    response = getattr(test_client, test_method.lower())(
        test_route, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 401


def test_serial_number__get__success(mocked_asyncpg_con):
    expected_db_entries = [
        {"serial_number": "123", "hw_version": "1.2.3"},
        {"serial_number": "444", "hw_version": "0.0.0"},
    ]
    # return a list of dicts here, but fetch will actually return a Record object with these keys/vals as attr names/vals
    mocked_asyncpg_con.fetch.return_value = expected_db_entries

    response = test_client.get("/serial-number")
    assert response.status_code == 200
    assert response.json() == {"units": expected_db_entries}


def test_serial_number__post__success(mocked_asyncpg_con):
    access_token = get_token(scope=["mantarray:serial_number:edit"])

    test_serial_number = "serial_number"
    test_hw_version = random_semver()

    response = test_client.post(
        "/serial-number",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"serial_number": test_serial_number, "hw_version": test_hw_version},
    )
    assert response.status_code == 201

    mocked_asyncpg_con.execute.assert_called_once_with(
        "INSERT INTO MAUnits VALUES ($1, $2)", test_serial_number, test_hw_version
    )


def test_serial_number__delete__success(mocked_asyncpg_con):
    access_token = get_token(scope=["mantarray:serial_number:edit"])

    test_serial_number = "serial_number"

    response = test_client.delete(
        f"/serial-number/{test_serial_number}", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 204

    mocked_asyncpg_con.execute.assert_called_once_with(
        "DELETE FROM MAUnits WHERE serial_number=$1", test_serial_number
    )


def test_software_range__get__success(mocker):
    mocked_get_required = mocker.patch.object(main, "get_required_sw_version_range", autospec=True)
    mocked_get_required.return_value = expected_max_min = {"min_sw": "1.1.1", "max_sw": "2.2.2"}

    test_main_fw_version = random_semver()

    response = test_client.get(f"/software-range/{test_main_fw_version}")
    assert response.status_code == 200
    assert response.json() == expected_max_min


def test_versions__get__success(mocked_asyncpg_con, mocker):
    expected_latest_fw_version = random_semver()
    mocked_get_latest_firmware_version = mocker.patch.object(
        main, "resolve_versions", autospec=True, return_value=expected_latest_fw_version
    )

    expected_hw_version = "2.2.2"
    mocked_asyncpg_con.fetchrow.return_value = {"hw_version": expected_hw_version}

    test_serial_number = "MA2022001000"
    response = test_client.get(f"/versions/{test_serial_number}")
    assert response.status_code == 200
    assert response.json() == {"latest_versions": expected_latest_fw_version}

    mocked_asyncpg_con.fetchrow.assert_called_once_with(
        "SELECT hw_version FROM MAUnits WHERE serial_number=$1", test_serial_number
    )
    mocked_get_latest_firmware_version.assert_called_once_with(expected_hw_version)


def test_versions__get__serial_number_not_found_in_db(mocked_asyncpg_con):
    mocked_asyncpg_con.fetchrow.side_effect = Exception()

    test_serial_number = "MA2022001000"
    response = test_client.get(f"/versions/{test_serial_number}")
    assert response.status_code == 404
    assert response.json() == {"message": f"Serial Number {test_serial_number} not found"}


def test_firmware_info__get__success(mocked_asyncpg_con):
    access_token = get_token(scope=["mantarray:firmware:info"])

    expected_response = main.FirmwareInfoResponse(
        main_fw_info=[{"main": "1.1.1"}], channel_fw_info=[{"channel": "2.2.2"}]
    )

    def fetch_se(query):
        if query == "SELECT * FROM ma_main_firmware":
            return expected_response.main_fw_info
        if query == "SELECT * FROM ma_channel_firmware":
            return expected_response.channel_fw_info
        return None

    mocked_asyncpg_con.fetch.side_effect = fetch_se

    response = test_client.get("/firmware/info", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json() == expected_response


def test_firmware__get__success(mocker):
    access_token = get_token(scope=["mantarray:firmware:get"])

    expected_url = "url"
    mocked_get_url = mocker.patch.object(main, "get_download_url", autospec=True, return_value=expected_url)

    test_firmware_version = random_semver()
    test_firmware_type = random_firmware_type()
    response = test_client.get(
        f"/firmware/{test_firmware_type}/{test_firmware_version}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"presigned_url": expected_url}

    mocked_get_url.assert_called_once_with(test_firmware_version, test_firmware_type)


@pytest.mark.parametrize("bad_param_type", ["firmware_version", "firmware_type"])
def test_firmware__get__bad_path_params(bad_param_type):
    access_token = get_token(scope=["mantarray:firmware:get"])

    test_params = {"firmware_version": random_semver(), "firmware_type": random_firmware_type()}
    # change one param to invalid value
    test_params[bad_param_type] = "bad"

    response = test_client.get(
        f"/firmware/{test_params['firmware_type']}/{test_params['firmware_version']}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 422, test_params


@pytest.mark.parametrize(
    "is_compatible_with_current_ma_sw, is_compatible_with_current_sting_sw", [(True, False), (False, True)]
)
def test_firmware__post__main_fw__success(
    mocker, mocked_asyncpg_con, is_compatible_with_current_ma_sw, is_compatible_with_current_sting_sw
):
    access_token = get_token(scope=["mantarray:firmware:edit"])

    test_fw_version = random_semver()

    def fetch_se(query):
        if query == "SELECT version FROM ma_controllers":
            return [{"version": v} for v in ("1.1.0", "11.1.0", "11.11.0", "1.11.0")]
        if query == "SELECT version FROM sting_controllers":
            return [{"version": v} for v in ("1.1.2", "11.1.2", "11.11.2", "1.11.2")]
        return None

    mocked_asyncpg_con.fetch.side_effect = fetch_se

    mocked_presigned_post = mocker.patch.object(
        main, "generate_presigned_post", autospec=True, return_value={"upload": "params"}
    )

    response = test_client.post(
        f"/firmware/main/{test_fw_version}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "version": test_fw_version,
            "is_compatible_with_current_ma_sw": is_compatible_with_current_ma_sw,
            "is_compatible_with_current_sting_sw": is_compatible_with_current_sting_sw,
            "md5s": "any",
        },
    )
    assert response.status_code == 200
    assert response.json() == FirmwareUploadResponse(params=mocked_presigned_post.return_value)

    mocked_asyncpg_con.execute.assert_called_with(
        "INSERT INTO ma_main_firmware (version, min_ma_controller_version, min_sting_controller_version) VALUES ($1, $2, $3)",
        test_fw_version,
        "11.11.0" if is_compatible_with_current_ma_sw else "11.11.1",
        "11.11.2" if is_compatible_with_current_sting_sw else "11.11.3",
    )


def test_firmware__post__channel_fw__success(mocker, mocked_asyncpg_con):
    access_token = get_token(scope=["mantarray:firmware:edit"])

    test_fw_version = random_semver()

    mocked_presigned_post = mocker.patch.object(
        main, "generate_presigned_post", autospec=True, return_value={"upload": "params"}
    )

    test_main_fw_version = random_semver()
    test_hw_version = random_semver()

    response = test_client.post(
        f"/firmware/channel/{test_fw_version}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "version": test_fw_version,
            "main_fw_version": test_main_fw_version,
            "hw_version": test_hw_version,
            "md5s": "any",
        },
    )
    assert response.status_code == 200
    assert response.json() == FirmwareUploadResponse(params=mocked_presigned_post.return_value)

    mocked_asyncpg_con.execute.assert_called_with(
        "INSERT INTO ma_channel_firmware (version, main_fw_version, hw_version) VALUES ($1, $2, $3)",
        test_fw_version,
        test_main_fw_version,
        test_hw_version,
    )


def test_firmware__put__success(mocker):
    # access_token = get_token(scope=["mantarray:firmware:edit"])

    assert not "TODO"


def test_software__post__success(mocker):
    # access_token = get_token(scope=["mantarray:software:edit"])

    assert not "TODO"
