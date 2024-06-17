from datetime import datetime, timedelta
import json
from random import choice, randint
import uuid

from argon2 import PasswordHasher
from asyncpg.exceptions import UniqueViolationError
from fastapi.testclient import TestClient
from freezegun import freeze_time
import pytest

from auth import (
    create_token,
    Scopes,
    ScopeTags,
    PULSE3D_PAID_USAGE,
    AuthTokens,
    get_assignable_user_scopes,
    get_assignable_admin_scopes,
    get_scope_dependencies,
    AccountTypes,
    LoginType,
)
from auth.settings import REFRESH_TOKEN_EXPIRE_MINUTES
from src import main
from src.models.users import (
    USERNAME_MIN_LEN,
    USERNAME_MAX_LEN,
    USERNAME_VALID_SPECIAL_CHARS,
    LoginResponse,
    UnableToUpdateAccountResponse,
)

test_client = TestClient(main.app)


TEST_PASSWORD = "Testpw123!"

ACCOUNT_SCOPES = tuple(s for s in Scopes if ScopeTags.ACCOUNT in s.tags)


def get_token(*, userid=None, customer_id=None, scopes=None, account_type=None, refresh=False):
    if not account_type:
        account_type = choice(list(AccountTypes))
    if not userid and account_type == AccountTypes.USER:
        userid = uuid.uuid4()
    if not customer_id:
        customer_id = uuid.uuid4()
    if not scopes:
        if refresh:
            scopes = [Scopes.REFRESH]
        else:
            scopes = (
                [Scopes.MANTARRAY__BASE] if account_type == AccountTypes.USER else [Scopes.MANTARRAY__ADMIN]
            )

    return create_token(
        userid=userid, customer_id=customer_id, scopes=scopes, account_type=account_type, refresh=refresh
    ).token


@pytest.fixture(scope="function", name="mocked_asyncpg_con", autouse=True)
async def fixture_mocked_asyncpg_con(mocker):
    mocked_asyncpg_pool = mocker.patch.object(main, "asyncpg_pool", autospec=True)

    mocked_asyncpg_pool_coroutine = mocker.AsyncMock()
    mocked_asyncpg_pool_coroutine.return_value = mocker.MagicMock()
    mocked_asyncpg_pool.return_value = mocked_asyncpg_pool_coroutine()

    mocked_asyncpg_con = await mocked_asyncpg_pool_coroutine.return_value.acquire().__aenter__()
    mocked_asyncpg_con.transaction = mocker.MagicMock()

    yield mocked_asyncpg_con


@pytest.fixture(scope="function", name="spied_pw_hasher")
def fixture_spied_pw_hasher(mocker):
    spied_pw_hasher = mocker.spy(main.PasswordHasher, "hash")
    yield spied_pw_hasher


@pytest.mark.parametrize(
    "method,route",
    [
        ("POST", "/register/user"),
        ("POST", "/register/admin"),
        ("POST", "/refresh"),
        ("POST", "/logout"),
        ("GET", "/"),
        ("PUT", f"/{uuid.uuid4()}"),
    ],
)
def test_routes_requiring_auth_without_tokens(method, route):
    assert getattr(test_client, method.lower())(route).status_code == 403


@freeze_time()
@pytest.mark.parametrize("send_client_type", [True, False])
@pytest.mark.parametrize("use_alias", [True, False])
def test_login__user__success(send_client_type, use_alias, mocked_asyncpg_con, mocker):
    mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={
            "current": {"uploads": "0", "jobs": "0"},
            "jobs_reached": False,
            "limits": {"expiration_date": "", "jobs": "-1", "uploads": "-1"},
            "uploads_reached": False,
        },
        autospec=True,
    )

    test_customer_id = uuid.uuid4()

    login_details = {
        "customer_id": "test_alias" if use_alias else str(test_customer_id),
        "username": "test_USERNAME",
        "password": "test_password",
    }
    if send_client_type:
        login_details["client_type"] = "dashboard"

    test_user_id = uuid.uuid4()
    test_scope = Scopes.MANTARRAY__BASE
    pw_hash = PasswordHasher().hash(login_details["password"])

    mocked_asyncpg_con.fetchrow.return_value = {
        "password": pw_hash,
        "id": test_user_id,
        "failed_login_attempts": 0,
        "suspended": False,
        "customer_id": test_customer_id,
        "customer_suspended": False,
    }
    mocked_asyncpg_con.fetch.return_value = [{"scope": test_scope.value}]
    spied_create_token = mocker.spy(main, "create_new_tokens")

    expected_access_token = create_token(
        userid=test_user_id,
        customer_id=test_customer_id,
        scopes=[test_scope],
        account_type=AccountTypes.USER,
        refresh=False,
    )
    expected_refresh_token = create_token(
        userid=test_user_id,
        customer_id=test_customer_id,
        scopes=[Scopes.REFRESH],
        account_type=AccountTypes.USER,
        refresh=True,
    )

    response = test_client.post("/login", json=login_details)
    assert response.status_code == 200

    assert (
        response.json()
        == LoginResponse(
            tokens=AuthTokens(access=expected_access_token, refresh=expected_refresh_token),
            usage_quota=None,
            user_scopes=None,
        ).model_dump()
    )

    expected_query = (
        "SELECT u.password, u.id, u.failed_login_attempts, u.suspended AS suspended, u.customer_id, c.suspended AS customer_suspended "
        "FROM users u JOIN customers c ON u.customer_id=c.id "
        "WHERE u.deleted_at IS NULL AND u.name=$1 AND c.alias IS NOT NULL AND LOWER(c.alias)=LOWER($2) "
        "AND u.verified='t' AND u.login_type=$3"
        if use_alias
        else "SELECT u.password, u.id, u.failed_login_attempts, u.suspended AS suspended, u.customer_id, c.suspended AS customer_suspended "
        "FROM users u JOIN customers c ON u.customer_id=c.id "
        "WHERE u.deleted_at IS NULL AND u.name=$1 AND u.customer_id=$2 AND u.verified='t' AND u.login_type=$3"
    )

    mocked_asyncpg_con.fetchrow.assert_called_once_with(
        expected_query, login_details["username"].lower(), login_details["customer_id"], "password"
    )
    mocked_asyncpg_con.fetch.assert_called_once_with(
        "SELECT scope FROM account_scopes WHERE user_id=$1", test_user_id
    )
    mocked_asyncpg_con.execute.assert_called_with(
        "UPDATE users SET refresh_token=$1 WHERE id=$2", expected_refresh_token.token, test_user_id
    )

    assert spied_create_token.call_count == 1


def test_login__user__no_matching_record_in_db(mocked_asyncpg_con):
    login_details = {
        "customer_id": str(uuid.uuid4()),
        "username": "test_USERNAME",
        "password": "test_password",
    }

    mocked_asyncpg_con.fetchrow.return_value = None

    response = test_client.post("/login", json=login_details)
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid credentials. Account will be locked after 10 failed attempts."
    }


def test_login__user__incorrect_password(mocked_asyncpg_con):
    login_details = {
        "customer_id": str(uuid.uuid4()),
        "username": "test_USERNAME",
        "password": "test_password",
    }

    mocked_asyncpg_con.fetchrow.return_value = {
        "password": "bad_hash",
        "id": uuid.uuid4(),
        "failed_login_attempts": 0,
        "suspended": False,
    }

    response = test_client.post("/login", json=login_details)
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid credentials. Account will be locked after 10 failed attempts."
    }


@pytest.mark.parametrize("login_attempts", [9, 10, 11])
def test_login__user__returns_locked_status_after_10_attempts(mocked_asyncpg_con, login_attempts):
    login_details = {
        "customer_id": str(uuid.uuid4()),
        "username": "test_USERNAME",
        "password": "test_password",
    }

    mocked_asyncpg_con.fetchrow.return_value = {
        "password": PasswordHasher().hash("bad_pass"),
        "id": uuid.uuid4(),
        "failed_login_attempts": login_attempts,
        "suspended": False,
    }

    response = test_client.post("/login", json=login_details)
    assert response.status_code == 401
    assert response.json() == {"detail": "Account locked. Too many failed attempts."}


def test_login__user__returns_invalid_creds_if_account_is_suspended(mocked_asyncpg_con):
    login_details = {
        "customer_id": str(uuid.uuid4()),
        "username": "test_USERNAME",
        "password": "test_password",
    }

    mocked_asyncpg_con.fetchrow.return_value = {
        "password": PasswordHasher().hash("bad_pass"),
        "id": uuid.uuid4(),
        "failed_login_attempts": 4,
        "suspended": True,
    }

    response = test_client.post("/login", json=login_details)
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid credentials. Account will be locked after 10 failed attempts."
    }


@freeze_time()
@pytest.mark.parametrize("send_client_type", [True, False])
def test_login__admin__success(send_client_type, mocked_asyncpg_con, mocker):
    mocked_usage_check = mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={
            "current": {"uploads": "0", "jobs": "0"},
            "jobs_reached": False,
            "limits": {"expiration_date": "", "jobs": "-1", "uploads": "-1"},
            "uploads_reached": False,
        },
        asutospec=True,
    )

    login_details = {"email": "TEST@email.com", "password": "test_password"}
    if send_client_type:
        login_details["client_type"] = "dashboard"

    pw_hash = PasswordHasher().hash(login_details["password"])
    test_customer_id = uuid.uuid4()
    admin_scope = Scopes.MANTARRAY__ADMIN

    mocked_asyncpg_con.fetchrow.return_value = {
        "password": pw_hash,
        "id": test_customer_id,
        "failed_login_attempts": 0,
        "suspended": False,
    }
    mocked_asyncpg_con.fetch.return_value = [{"scope": admin_scope.value}]
    spied_create_token = mocker.spy(main, "create_new_tokens")

    expected_access_token = create_token(
        userid=None,
        customer_id=test_customer_id,
        scopes=[admin_scope],
        account_type=AccountTypes.ADMIN,
        refresh=False,
    )
    expected_refresh_token = create_token(
        userid=None,
        customer_id=test_customer_id,
        scopes=[Scopes.REFRESH],
        account_type=AccountTypes.ADMIN,
        refresh=True,
    )

    response = test_client.post("/login/admin", json=login_details)
    assert response.status_code == 200
    assert (
        response.json()
        == LoginResponse(
            tokens=AuthTokens(access=expected_access_token, refresh=expected_refresh_token),
            usage_quota=mocked_usage_check.return_value,
            user_scopes=get_scope_dependencies(get_assignable_user_scopes([admin_scope])),
            admin_scopes=get_scope_dependencies(get_assignable_admin_scopes([admin_scope])),
        ).model_dump()
    )

    mocked_asyncpg_con.fetchrow.assert_called_once_with(
        "SELECT password, id, failed_login_attempts, suspended FROM customers WHERE deleted_at IS NULL AND email=$1 AND login_type=$2",
        login_details["email"].lower(),
        "password",
    )
    mocked_asyncpg_con.fetch.assert_called_once_with(
        "SELECT scope FROM account_scopes WHERE customer_id=$1 AND user_id IS NULL", test_customer_id
    )
    mocked_asyncpg_con.execute.assert_called_with(
        "UPDATE customers SET refresh_token=$1 WHERE id=$2", expected_refresh_token.token, test_customer_id
    )

    assert spied_create_token.call_count == 1


def test_login__admin__no_matching_record_in_db(mocked_asyncpg_con):
    login_details = {"email": "test@email.com", "password": "test_password", "service": "pulse3d"}

    mocked_asyncpg_con.fetchrow.return_value = None

    response = test_client.post("/login/admin", json=login_details)
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid credentials. Account will be locked after 10 failed attempts."
    }


def test_login__admin__incorrect_password(mocked_asyncpg_con):
    login_details = {"email": "test@email.com", "password": "test_password", "service": "pulse3d"}

    mocked_asyncpg_con.fetchrow.return_value = {
        "password": "bad_hash",
        "id": uuid.uuid4(),
        "failed_login_attempts": 0,
        "suspended": False,
    }

    response = test_client.post("/login/admin", json=login_details)
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid credentials. Account will be locked after 10 failed attempts."
    }


@pytest.mark.parametrize("login_attempts", [9, 10, 11])
def test_login__admin__returns_locked_status_after_10_attempts(mocked_asyncpg_con, login_attempts):
    login_details = {"email": "test@email.com", "password": "test_password", "service": "pulse3d"}

    mocked_asyncpg_con.fetchrow.return_value = {
        "password": PasswordHasher().hash("bad_pass"),
        "id": uuid.uuid4(),
        "failed_login_attempts": login_attempts,
        "suspended": False,
    }

    response = test_client.post("/login/admin", json=login_details)
    assert response.status_code == 401
    assert response.json() == {"detail": "Account locked. Too many failed attempts."}


def test_login__admin__returns_invalid_creds_if_account_is_suspended(mocked_asyncpg_con):
    login_details = {"email": "test@email.com", "password": "test_password", "service": "pulse3d"}

    mocked_asyncpg_con.fetchrow.return_value = {
        "password": PasswordHasher().hash("bad_pass"),
        "id": uuid.uuid4(),
        "failed_login_attempts": 4,
        "suspended": True,
    }

    response = test_client.post("/login/admin", json=login_details)
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid credentials. Account will be locked after 10 failed attempts."
    }


@freeze_time()
@pytest.mark.parametrize("send_client_type", [True, False])
def test_sso__user__success(send_client_type, mocked_asyncpg_con, mocker):
    email = "TEST3@email.com"
    mocker.patch.object(main, "_decode_and_verify_jwt", return_value={"email": email})

    sso_details = {"id_token": "sometoken"}
    if send_client_type:
        sso_details["client_type"] = "dashboard"

    test_customer_id = uuid.uuid4()
    test_user_id = uuid.uuid4()
    test_scope = Scopes.MANTARRAY__BASE

    mocked_asyncpg_con.fetchrow.return_value = {
        "id": test_user_id,
        "suspended": False,
        "customer_id": test_customer_id,
        "customer_suspended": False,
    }
    mocked_asyncpg_con.fetch.return_value = [{"scope": test_scope.value}]
    spied_create_token = mocker.spy(main, "create_new_tokens")

    expected_access_token = create_token(
        userid=test_user_id,
        customer_id=test_customer_id,
        scopes=[test_scope],
        account_type=AccountTypes.USER,
        login_type=LoginType.SSO_MICROSOFT,
        refresh=False,
    )
    expected_refresh_token = create_token(
        userid=test_user_id,
        customer_id=test_customer_id,
        scopes=[Scopes.REFRESH],
        account_type=AccountTypes.USER,
        login_type=LoginType.SSO_MICROSOFT,
        refresh=True,
    )

    response = test_client.post("/sso", json=sso_details)
    assert response.status_code == 200

    assert (
        response.json()
        == LoginResponse(
            tokens=AuthTokens(access=expected_access_token, refresh=expected_refresh_token),
            usage_quota=None,
            user_scopes=None,
        ).model_dump()
    )

    expected_query = (
        "SELECT u.id, u.suspended AS suspended, u.customer_id, c.suspended AS customer_suspended "
        "FROM users u JOIN customers c ON u.customer_id=c.id "
        "WHERE u.deleted_at IS NULL AND u.email=$1 AND u.login_type!=$2"
    )

    mocked_asyncpg_con.fetchrow.assert_called_once_with(expected_query, email, "password")
    mocked_asyncpg_con.fetch.assert_called_once_with(
        "SELECT scope FROM account_scopes WHERE user_id=$1", test_user_id
    )
    mocked_asyncpg_con.execute.assert_called_with(
        "UPDATE users SET refresh_token=$1 WHERE id=$2", expected_refresh_token.token, test_user_id
    )

    assert spied_create_token.call_count == 1


def test_sso__user__no_matching_record_in_db(mocked_asyncpg_con, mocker):
    sso_details = {"id_token": "sometoken"}
    mocker.patch.object(main, "_decode_and_verify_jwt", return_value={"email": "TEST4@email.com"})
    mocked_asyncpg_con.fetchrow.return_value = None

    response = test_client.post("/sso", json=sso_details)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials."}


def test_sso__user__returns_invalid_creds_if_account_is_suspended(mocked_asyncpg_con, mocker):
    sso_details = {"id_token": "sometoken"}
    mocker.patch.object(main, "_decode_and_verify_jwt", return_value={"email": "TEST4@email.com"})
    mocked_asyncpg_con.fetchrow.return_value = {
        "id": uuid.uuid4(),
        "suspended": True,
        "customer_id": uuid.uuid4(),
        "customer_suspended": False,
    }

    response = test_client.post("/sso", json=sso_details)
    assert response.status_code == 401
    assert response.json() == {"detail": "Account has been suspended."}


def test_sso__user__returns_invalid_creds_if_customer_account_is_suspended(mocked_asyncpg_con, mocker):
    sso_details = {"id_token": "sometoken"}
    mocker.patch.object(main, "_decode_and_verify_jwt", return_value={"email": "TEST4@email.com"})
    mocked_asyncpg_con.fetchrow.return_value = {
        "id": uuid.uuid4(),
        "suspended": False,
        "customer_id": uuid.uuid4(),
        "customer_suspended": True,
    }

    response = test_client.post("/sso", json=sso_details)
    assert response.status_code == 401
    assert response.json() == {"detail": "The customer ID for this account has been deactivated."}


@freeze_time()
@pytest.mark.parametrize("send_client_type", [True, False])
def test_sso__admin__success(send_client_type, mocked_asyncpg_con, mocker):
    email = "TEST@email.com"
    tid = "testtid"
    oid = "testoid"
    mocker.patch.object(main, "_decode_and_verify_jwt", return_value={"email": email, "tid": tid, "oid": oid})

    mocked_usage_check = mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={
            "current": {"uploads": "0", "jobs": "0"},
            "jobs_reached": False,
            "limits": {"expiration_date": "", "jobs": "-1", "uploads": "-1"},
            "uploads_reached": False,
        },
        autospec=True,
    )

    sso_details = {"id_token": "sometoken"}
    if send_client_type:
        sso_details["client_type"] = "dashboard"

    test_customer_id = uuid.uuid4()
    admin_scope = Scopes.MANTARRAY__ADMIN

    mocked_asyncpg_con.fetchrow.return_value = {"id": test_customer_id, "suspended": False}
    mocked_asyncpg_con.fetch.return_value = [{"scope": admin_scope.value}]
    spied_create_token = mocker.spy(main, "create_new_tokens")

    expected_access_token = create_token(
        userid=None,
        customer_id=test_customer_id,
        scopes=[admin_scope],
        account_type=AccountTypes.ADMIN,
        login_type=LoginType.SSO_MICROSOFT,
        refresh=False,
    )
    expected_refresh_token = create_token(
        userid=None,
        customer_id=test_customer_id,
        scopes=[Scopes.REFRESH],
        account_type=AccountTypes.ADMIN,
        login_type=LoginType.SSO_MICROSOFT,
        refresh=True,
    )

    response = test_client.post("/sso/admin", json=sso_details)
    assert response.status_code == 200
    assert (
        response.json()
        == LoginResponse(
            tokens=AuthTokens(access=expected_access_token, refresh=expected_refresh_token),
            usage_quota=mocked_usage_check.return_value,
            user_scopes=get_scope_dependencies(get_assignable_user_scopes([admin_scope])),
            admin_scopes=get_scope_dependencies(get_assignable_admin_scopes([admin_scope])),
        ).model_dump()
    )

    mocked_asyncpg_con.fetchrow.assert_called_once_with(
        "SELECT id, suspended FROM customers WHERE deleted_at IS NULL AND "
        "email=$1 AND login_type!=$2 AND sso_organization=$3 AND sso_admin_org_id=$4",
        email,
        "password",
        tid,
        oid,
    )
    mocked_asyncpg_con.fetch.assert_called_once_with(
        "SELECT scope FROM account_scopes WHERE customer_id=$1 AND user_id IS NULL", test_customer_id
    )
    mocked_asyncpg_con.execute.assert_called_with(
        "UPDATE customers SET refresh_token=$1 WHERE id=$2", expected_refresh_token.token, test_customer_id
    )

    assert spied_create_token.call_count == 1


def test_sso__admin__no_matching_record_in_db(mocked_asyncpg_con, mocker):
    sso_details = {"id_token": "sometoken"}
    mocker.patch.object(main, "_decode_and_verify_jwt", return_value={"email": "TEST@email.com"})
    mocked_asyncpg_con.fetchrow.return_value = None

    response = test_client.post("/sso/admin", json=sso_details)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials."}


def test_sso__admin__returns_invalid_creds_if_account_is_suspended(mocked_asyncpg_con, mocker):
    sso_details = {"id_token": "sometoken"}
    mocker.patch.object(main, "_decode_and_verify_jwt", return_value={"email": "TEST@email.com"})
    mocked_asyncpg_con.fetchrow.return_value = {"id": uuid.uuid4(), "suspended": True}

    response = test_client.post("/sso/admin", json=sso_details)
    assert response.status_code == 401
    assert response.json() == {"detail": "Account has been suspended."}


@pytest.mark.parametrize("special_char", ["", *USERNAME_VALID_SPECIAL_CHARS])
def test_register__user__success(special_char, mocked_asyncpg_con, mocker):
    mocker.patch.object(main, "_create_account_email", autospec=True)
    end_with_num = choice([True, False])

    expected_scopes = [Scopes.MANTARRAY__RW_ALL_DATA, Scopes.MANTARRAY__FIRMWARE__GET]

    registration_details = {
        "email": "USEr@example.com",
        "username": f"Test{special_char}UseRName",
        "scopes": expected_scopes,
    }

    if end_with_num:
        registration_details["username"] += str(randint(0, 9))

    test_user_id = uuid.uuid4()
    test_customer_id = uuid.uuid4()
    access_token = get_token(customer_id=test_customer_id, account_type=AccountTypes.ADMIN)

    mocked_asyncpg_con.fetchval.side_effect = ["password", test_user_id]

    response = test_client.post(
        "/register/user", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.json() == {
        "username": registration_details["username"].lower(),
        "email": registration_details["email"].lower(),
        "user_id": test_user_id.hex,
        "scopes": expected_scopes,
    }
    assert response.status_code == 201

    mocked_asyncpg_con.fetchval.assert_has_calls(
        [
            mocker.call("SELECT login_type FROM customers WHERE id=$1", test_customer_id),
            mocker.call(
                "INSERT INTO users (name, email, customer_id, login_type, verified) "
                "VALUES ($1, $2, $3, $4, $5) RETURNING id",
                registration_details["username"].lower(),
                registration_details["email"].lower(),
                test_customer_id,
                "password",
                False,
            ),
        ]
    )
    mocked_asyncpg_con.execute.assert_called_once_with(
        "INSERT INTO account_scopes VALUES ($1, $2, unnest($3::text[]))",
        test_customer_id,
        test_user_id,
        expected_scopes,
    )


def test_register__user__sso__success(mocked_asyncpg_con, mocker):
    mocker.patch.object(main, "_send_account_email", autospec=True)

    expected_scopes = [Scopes.MANTARRAY__RW_ALL_DATA, Scopes.MANTARRAY__FIRMWARE__GET]

    registration_details = {
        "email": "USEr@example.com",
        "username": "TestUseRName",
        "scopes": expected_scopes,
    }

    test_user_id = uuid.uuid4()
    test_customer_id = uuid.uuid4()
    access_token = get_token(customer_id=test_customer_id, account_type=AccountTypes.ADMIN)

    mocked_asyncpg_con.fetchval.side_effect = ["sso_microsoft", test_user_id]

    response = test_client.post(
        "/register/user", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.json() == {
        "username": registration_details["username"].lower(),
        "email": registration_details["email"].lower(),
        "user_id": test_user_id.hex,
        "scopes": expected_scopes,
    }
    assert response.status_code == 201

    mocked_asyncpg_con.fetchval.assert_has_calls(
        [
            mocker.call("SELECT login_type FROM customers WHERE id=$1", test_customer_id),
            mocker.call(
                "INSERT INTO users (name, email, customer_id, login_type, verified) "
                "VALUES ($1, $2, $3, $4, $5) RETURNING id",
                registration_details["username"].lower(),
                registration_details["email"].lower(),
                test_customer_id,
                "sso_microsoft",
                True,
            ),
        ]
    )
    mocked_asyncpg_con.execute.assert_called_once_with(
        "INSERT INTO account_scopes VALUES ($1, $2, unnest($3::text[]))",
        test_customer_id,
        test_user_id,
        expected_scopes,
    )


@pytest.mark.parametrize(
    "test_admin_scope,test_user_scope",
    [
        (Scopes.MANTARRAY__ADMIN, Scopes.NAUTILAI__BASE),
        (Scopes.MANTARRAY__ADMIN, Scopes.MANTARRAY__FIRMWARE__EDIT),
        (Scopes.NAUTILAI__ADMIN, Scopes.MANTARRAY__BASE),
        (Scopes.MANTARRAY__ADMIN, Scopes.CURI__ADMIN),
        (Scopes.NAUTILAI__ADMIN, Scopes.CURI__ADMIN),
        (Scopes.CURI__ADMIN, Scopes.CURI__ADMIN),
    ],
)
def test_register__user__invalid_token_scope_assigned(test_admin_scope, test_user_scope):
    registration_details = {"email": "user@example.com", "username": "username", "scopes": [test_user_scope]}
    access_token = get_token(scopes=[test_admin_scope], account_type=AccountTypes.ADMIN)
    response = test_client.post(
        "/register/user", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "length,err_msg",
    [
        (USERNAME_MIN_LEN - 1, "Username does not meet min length"),
        (USERNAME_MAX_LEN + 1, "Username exceeds max length"),
    ],
)
def test_register__user__invalid_username_length(length, err_msg):
    registration_details = {
        "email": "test@email.com",
        "username": "a" * length,
        "scopes": [Scopes.MANTARRAY__BASE],
    }

    test_customer_id = uuid.uuid4()
    access_token = get_token(customer_id=test_customer_id, account_type=AccountTypes.ADMIN)

    response = test_client.post(
        "/register/user", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 422
    assert response.json()["detail"][-1]["msg"].endswith(err_msg)


@pytest.mark.parametrize("special_char", ["@", "#", "$", "*", "&", "%"])
def test_register__user__with_invalid_char_in_username(special_char):
    registration_details = {
        "email": "test@email.com",
        "username": f"bad{special_char}username",
        "scopes": [Scopes.MANTARRAY__BASE],
    }

    access_token = get_token(account_type=AccountTypes.ADMIN)

    response = test_client.post(
        "/register/user", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 422
    assert response.json()["detail"][-1]["msg"].endswith(
        f"Username can only contain letters, numbers, and these special characters: {USERNAME_VALID_SPECIAL_CHARS}"
    )


@pytest.mark.parametrize("bad_first_char", [*USERNAME_VALID_SPECIAL_CHARS, str(randint(0, 9))])
def test_register__user__with_invalid_first_char(bad_first_char):
    registration_details = {
        "email": "test@email.com",
        "username": f"{bad_first_char}username",
        "scopes": [Scopes.MANTARRAY__BASE],
    }

    access_token = get_token(account_type=AccountTypes.ADMIN)

    response = test_client.post(
        "/register/user", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 422
    assert response.json()["detail"][-1]["msg"].endswith("Username must start with a letter")


@pytest.mark.parametrize("bad_final_char", USERNAME_VALID_SPECIAL_CHARS)
def test_register__user__with_invalid_final_char(bad_final_char):
    registration_details = {
        "email": "test@email.com",
        "username": f"username{bad_final_char}",
        "scopes": [Scopes.MANTARRAY__BASE],
    }

    access_token = get_token(account_type=AccountTypes.ADMIN)

    response = test_client.post(
        "/register/user", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 422
    assert response.json()["detail"][-1]["msg"].endswith("Username must end with a letter or number")


@pytest.mark.parametrize("special_char", USERNAME_VALID_SPECIAL_CHARS)
def test_register__user__with_consecutive_special_chars(special_char):
    registration_details = {
        "email": "test@email.com",
        "username": f"a-{special_char}a",
        "scopes": [Scopes.MANTARRAY__BASE],
    }

    access_token = get_token(scopes=[Scopes.MANTARRAY__ADMIN], account_type=AccountTypes.ADMIN)

    response = test_client.post(
        "/register/user", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 422
    assert response.json()["detail"][-1]["msg"].endswith(
        "Username cannot contain consecutive special characters"
    )


@pytest.mark.parametrize(
    "contraint_to_violate,expected_error_message",
    [
        ("users_customer_id_name_key", "Username already in use"),
        ("users_email_key", "Email already in use"),
        ("all others", "Account registration failed"),
    ],
)
def test_register__user__unique_constraint_violations(
    contraint_to_violate, expected_error_message, mocked_asyncpg_con
):
    registration_details = {
        "email": "test@email.com",
        "username": "testusername",
        "scopes": [Scopes.MANTARRAY__BASE, Scopes.NAUTILAI__BASE],
    }

    access_token = get_token(
        scopes=[Scopes.MANTARRAY__ADMIN, Scopes.NAUTILAI__ADMIN], account_type=AccountTypes.ADMIN
    )

    mocked_asyncpg_con.fetchval.side_effect = UniqueViolationError(contraint_to_violate)

    response = test_client.post(
        "/register/user", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": expected_error_message}


def test_register__user__invalid_token_scope_given():
    registration_details = {"email": "user@new.com", "password1": "pw", "password2": "pw"}
    access_token = get_token(scopes=[Scopes.MANTARRAY__BASE], account_type=AccountTypes.USER)
    response = test_client.post(
        "/register/user", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 401


def test_register__admin__success(mocked_asyncpg_con, spied_pw_hasher, mocker):
    mocker.patch.object(main, "_create_account_email", autospec=True)

    expected_scopes = [Scopes.MANTARRAY__ADMIN, Scopes.NAUTILAI__ADMIN]
    registration_details = {
        "email": "tEsT@email.com",
        "password1": TEST_PASSWORD,
        "password2": TEST_PASSWORD,
        "scopes": expected_scopes,
    }

    test_user_id = uuid.uuid4()
    test_customer_id = uuid.uuid4()
    access_token = get_token(
        customer_id=test_customer_id, scopes=[Scopes.CURI__ADMIN], account_type=AccountTypes.ADMIN
    )

    mocked_asyncpg_con.fetchval.return_value = test_user_id

    response = test_client.post(
        "/register/admin", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 201
    assert response.json() == {
        "email": registration_details["email"].lower(),
        "user_id": test_user_id.hex,
        "scopes": expected_scopes,
    }

    mocked_asyncpg_con.fetchval.assert_called_once_with(
        "INSERT INTO customers (email, usage_restrictions, login_type, sso_organization, sso_admin_org_id) "
        "VALUES ($1, $2, $3, $4, $5) RETURNING id",
        registration_details["email"].lower(),
        json.dumps(dict(PULSE3D_PAID_USAGE)),
        "password",
        None,
        None,
    )
    mocked_asyncpg_con.execute.assert_called_once_with(
        "INSERT INTO account_scopes VALUES ($1, NULL, unnest($2::text[]))", test_user_id, expected_scopes
    )


def test_register__admin__login_type_sso_microsoft_success(mocked_asyncpg_con, spied_pw_hasher, mocker):
    mocker.patch.object(main, "_send_account_email", autospec=True)

    expected_scopes = [Scopes.MANTARRAY__ADMIN, Scopes.NAUTILAI__ADMIN]
    registration_details = {
        "email": "tEsT@email.com",
        "scopes": expected_scopes,
        "login_type": "sso_microsoft",
        "sso_organization": "some-organization",
        "sso_admin_org_id": "some-admin-org-id",
    }

    test_user_id = uuid.uuid4()
    test_customer_id = uuid.uuid4()
    access_token = get_token(
        customer_id=test_customer_id, scopes=[Scopes.CURI__ADMIN], account_type=AccountTypes.ADMIN
    )

    mocked_asyncpg_con.fetchval.return_value = test_user_id

    response = test_client.post(
        "/register/admin", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 201
    assert response.json() == {
        "email": registration_details["email"].lower(),
        "user_id": test_user_id.hex,
        "scopes": expected_scopes,
    }

    mocked_asyncpg_con.fetchval.assert_called_once_with(
        "INSERT INTO customers (email, usage_restrictions, login_type, sso_organization, sso_admin_org_id) "
        "VALUES ($1, $2, $3, $4, $5) RETURNING id",
        registration_details["email"].lower(),
        json.dumps(dict(PULSE3D_PAID_USAGE)),
        "sso_microsoft",
        "some-organization",
        "some-admin-org-id",
    )
    mocked_asyncpg_con.execute.assert_called_once_with(
        "INSERT INTO account_scopes VALUES ($1, NULL, unnest($2::text[]))", test_user_id, expected_scopes
    )


def test_register__admin__login_type_invalid(mocked_asyncpg_con, spied_pw_hasher, mocker):
    mocker.patch.object(main, "_send_account_email", autospec=True)

    expected_scopes = [Scopes.MANTARRAY__ADMIN, Scopes.NAUTILAI__ADMIN]
    registration_details = {
        "email": "tEsT@email.com",
        "password1": TEST_PASSWORD,
        "password2": TEST_PASSWORD,
        "scopes": expected_scopes,
        "login_type": "sso_google",
    }

    test_user_id = uuid.uuid4()
    test_customer_id = uuid.uuid4()
    access_token = get_token(
        customer_id=test_customer_id, scopes=[Scopes.CURI__ADMIN], account_type=AccountTypes.ADMIN
    )

    mocked_asyncpg_con.fetchval.return_value = test_user_id

    response = test_client.post(
        "/register/admin", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 422  # sso_google is not a valid login_type


@pytest.mark.parametrize(
    "test_admin_scope", [Scopes.CURI__ADMIN, Scopes.NAUTILAI__BASE, Scopes.MANTARRAY__BASE]
)
def test_register__admin__invalid_token_scope_assigned(test_admin_scope):
    registration_details = {
        "email": "test@email.com",
        "password1": TEST_PASSWORD,
        "password2": TEST_PASSWORD,
        "scopes": [test_admin_scope],
    }
    access_token = get_token(scopes=[Scopes.CURI__ADMIN], account_type=AccountTypes.ADMIN)
    response = test_client.post(
        "/register/admin", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "contraint_to_violate,expected_error_message",
    [("customers_email_key", "Email already in use"), ("all others", "Customer registration failed")],
)
def test_register__admin__unique_constraint_violations(
    contraint_to_violate, expected_error_message, mocked_asyncpg_con, spied_pw_hasher, mocker
):
    test_scope = [Scopes.NAUTILAI__ADMIN]

    registration_details = {
        "email": "test@email.com",
        "password1": TEST_PASSWORD,
        "password2": TEST_PASSWORD,
        "scopes": test_scope,
    }

    test_customer_id = uuid.uuid4()

    access_token = get_token(
        customer_id=test_customer_id, scopes=[Scopes.CURI__ADMIN], account_type=AccountTypes.ADMIN
    )

    mocked_asyncpg_con.fetchval.side_effect = UniqueViolationError(contraint_to_violate)

    response = test_client.post(
        "/register/admin", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": expected_error_message}


def test_register__admin__invalid_token_scope_given():
    registration_details = {
        "email": "test@email.com",
        "password1": TEST_PASSWORD,
        "password2": TEST_PASSWORD,
        "scopes": ["any"],
    }
    access_token = get_token(scopes=[Scopes.NAUTILAI__ADMIN], account_type=AccountTypes.ADMIN)
    response = test_client.post(
        "/register/admin", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 401


@freeze_time()
@pytest.mark.parametrize("account_type", list(AccountTypes))
def test_refresh__success(account_type, mocked_asyncpg_con):
    is_admin_account = account_type == AccountTypes.ADMIN
    userid = None if is_admin_account else uuid.uuid4()
    customer_id = uuid.uuid4()

    # arbitrarily choosing this scope
    test_scope_in_db = Scopes.MANTARRAY__ADMIN if is_admin_account else Scopes.MANTARRAY__BASE

    select_clause = "refresh_token"
    if account_type == AccountTypes.USER:
        select_clause += ", customer_id"

    refresh_scope = [Scopes.REFRESH]

    old_refresh_token = get_token(
        userid=userid, customer_id=customer_id, scopes=refresh_scope, account_type=account_type, refresh=True
    )

    new_access_token = create_token(
        userid=userid,
        customer_id=customer_id,
        scopes=[test_scope_in_db],
        account_type=account_type,
        refresh=False,
    )
    new_refresh_token = create_token(
        userid=userid, customer_id=customer_id, scopes=refresh_scope, account_type=account_type, refresh=True
    )

    mocked_asyncpg_con.fetchrow.return_value = {"refresh_token": old_refresh_token}
    if not is_admin_account:
        mocked_asyncpg_con.fetchrow.return_value["customer_id"] = customer_id
    mocked_asyncpg_con.fetch.return_value = [{"scope": test_scope_in_db.value}]

    response = test_client.post("/refresh", headers={"Authorization": f"Bearer {old_refresh_token}"})
    assert response.status_code == 201
    assert response.json() == AuthTokens(access=new_access_token, refresh=new_refresh_token).model_dump()

    expected_fetch_query = (
        "SELECT scope FROM account_scopes WHERE customer_id=$1 AND user_id IS NULL"
        if is_admin_account
        else "SELECT scope FROM account_scopes WHERE user_id=$1"
    )

    account_id = customer_id if is_admin_account else userid
    mocked_asyncpg_con.fetchrow.assert_called_once_with(
        f"SELECT {select_clause} FROM {account_type}s WHERE id=$1", account_id
    )
    mocked_asyncpg_con.fetch.assert_called_once_with(expected_fetch_query, account_id)
    mocked_asyncpg_con.execute.assert_called_once_with(
        f"UPDATE {account_type}s SET refresh_token=$1 WHERE id=$2", old_refresh_token, account_id
    )


def test_refresh__expired_refresh_token_in_db(mocked_asyncpg_con):
    test_time = datetime.now()

    with freeze_time(test_time):
        old_refresh_token = get_token(refresh=True)
        mocked_asyncpg_con.fetchval.return_value = old_refresh_token

    with freeze_time(test_time + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES, seconds=1)):
        response = test_client.post("/refresh", headers={"Authorization": f"Bearer {old_refresh_token}"})
        assert response.status_code == 401


def test_refresh__wrong_token_type_given():
    access_token = get_token(refresh=False)
    response = test_client.post("/refresh", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 401


@pytest.mark.parametrize("account_type", list(AccountTypes))
def test_logout__success(account_type, mocked_asyncpg_con):
    test_user_id = uuid.uuid4() if account_type == AccountTypes.USER else None
    test_customer_id = uuid.uuid4()
    access_token = get_token(userid=test_user_id, customer_id=test_customer_id, account_type=account_type)

    response = test_client.post("/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 204

    expected_account_id = test_user_id if account_type == AccountTypes.USER else test_customer_id
    mocked_asyncpg_con.execute.assert_called_once_with(
        f"UPDATE {account_type}s SET refresh_token = NULL WHERE id=$1", expected_account_id
    )


def test_account_id__get__no_id(mocked_asyncpg_con):
    test_customer_id = uuid.uuid4()
    access_token = get_token(customer_id=test_customer_id, account_type=AccountTypes.ADMIN)

    num_users_found = 3
    mocked_asyncpg_con.fetch.return_value = expected_users_info = [
        {
            "id": uuid.uuid4(),
            "name": f"name{i}",
            "email": f"user{i}@email.com",
            "created_at": datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
            "last_login": datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
            "verified": True,
            "suspended": choice([True, False]),
            "reset_token": None,
            "scopes": [Scopes.MANTARRAY__BASE],
        }
        for i in range(num_users_found)
    ]

    response = test_client.get("/", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200

    # convert IDs to a string since fastapi does this automatically
    for user_info in expected_users_info:
        user_info["id"] = str(user_info["id"])

    assert response.json() == expected_users_info

    mocked_asyncpg_con.fetch.assert_called_once_with(
        "SELECT u.id, u.name, u.email, u.created_at, u.last_login, u.verified, u.suspended, u.reset_token, array_agg(s.scope) as scopes FROM users u INNER JOIN account_scopes s ON u.id=s.user_id WHERE u.customer_id=$1 AND u.deleted_at IS NULL GROUP BY u.id, u.name, u.email, u.created_at, u.last_login, u.verified, u.suspended, u.reset_token ORDER BY u.suspended",
        test_customer_id,
    )


def test_account_id__get__no_id__invalid_token_scope_given():
    access_token = get_token(account_type=AccountTypes.USER)
    response = test_client.get("/", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 401


def test_account_id__get__id_given__admin_retrieving_self(mocked_asyncpg_con):
    test_customer_id = uuid.uuid4()
    access_token = get_token(customer_id=test_customer_id, account_type=AccountTypes.ADMIN)

    mocked_asyncpg_con.fetchrow.return_value = expected_customer_info = {
        "id": test_customer_id,
        "created_at": datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
        "alias": "test_alias",
    }

    response = test_client.get(f"/{test_customer_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200

    # convert ID to a string since fastapi does this automatically
    expected_customer_info["id"] = str(expected_customer_info["id"])

    assert response.json() == expected_customer_info

    mocked_asyncpg_con.fetchrow.assert_called_once_with(
        f"SELECT {', '.join(expected_customer_info)} FROM customers WHERE id=$1", test_customer_id
    )


def test_account_id__get__id_given__admin_retrieving_user__success(mocked_asyncpg_con):
    test_customer_id = uuid.uuid4()
    access_token = get_token(customer_id=test_customer_id, account_type=AccountTypes.ADMIN)

    test_user_id = uuid.uuid4()

    mocked_asyncpg_con.fetchrow.return_value = expected_user_info = {
        "id": uuid.uuid4(),
        "name": "name",
        "email": "user@email.com",
        "created_at": datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
        "last_login": datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
        "suspended": choice([True, False]),
    }

    response = test_client.get(f"/{test_user_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200

    # convert ID to a string since fastapi does this automatically
    expected_user_info["id"] = str(expected_user_info["id"])

    assert response.json() == expected_user_info

    mocked_asyncpg_con.fetchrow.assert_called_once_with(
        f"SELECT {', '.join(expected_user_info)} FROM users WHERE customer_id=$1 AND id=$2 AND deleted_at IS NULL",
        test_customer_id,
        test_user_id,
    )


def test_account_id__get__id_given__admin_retrieving_user__user_not_found(mocked_asyncpg_con):
    test_customer_id = uuid.uuid4()
    access_token = get_token(customer_id=test_customer_id, account_type=AccountTypes.ADMIN)

    test_user_id = uuid.uuid4()

    mocked_asyncpg_con.fetchrow.return_value = None

    response = test_client.get(f"/{test_user_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 400


def test_account_id__get__id_given__user_retrieving_self(mocked_asyncpg_con):
    test_user_id = uuid.uuid4()
    test_customer_id = uuid.uuid4()
    access_token = get_token(
        userid=test_user_id, customer_id=test_customer_id, account_type=AccountTypes.USER
    )

    mocked_asyncpg_con.fetchrow.return_value = expected_user_info = {
        "id": test_user_id,
        "name": "name",
        "email": "user@email.com",
        "created_at": datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
        "last_login": datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
        "suspended": choice([True, False]),
    }

    response = test_client.get(f"/{test_user_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200

    # convert ID to a string since fastapi does this automatically
    expected_user_info["id"] = str(expected_user_info["id"])

    assert response.json() == expected_user_info

    mocked_asyncpg_con.fetchrow.assert_called_once_with(
        f"SELECT {', '.join(expected_user_info)} FROM users WHERE customer_id=$1 AND id=$2 AND deleted_at IS NULL",
        test_customer_id,
        test_user_id,
    )


def test_account_id__get__id_given__user_attempting_to_retrieve_another_id(mocked_asyncpg_con):
    access_token = get_token(account_type=AccountTypes.USER)

    response = test_client.get(f"/{uuid.uuid4()}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 400


def test_account_id__get__id_given__user_not_found(mocked_asyncpg_con):
    access_token = get_token(account_type=AccountTypes.ADMIN)

    mocked_asyncpg_con.fetchrow.return_value = None

    response = test_client.get(f"/{uuid.uuid4()}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 400


@freeze_time()
def test_account_id__put__successful_user_deletion(mocked_asyncpg_con):
    test_customer_id = uuid.uuid4()
    access_token = get_token(customer_id=test_customer_id, account_type=AccountTypes.ADMIN)

    test_user_id = uuid.uuid4()

    response = test_client.put(
        f"/{test_user_id}",
        json={"action_type": "delete"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200

    mocked_asyncpg_con.execute.assert_called_once_with(
        "UPDATE users SET deleted_at=$1 WHERE id=$2 AND customer_id=$3",
        datetime.now(),
        test_user_id,
        test_customer_id,
    )


def test_user_id__put__successful_deactivation(mocked_asyncpg_con):
    test_customer_id = uuid.uuid4()
    access_token = get_token(customer_id=test_customer_id, account_type=AccountTypes.ADMIN)

    test_user_id = uuid.uuid4()

    response = test_client.put(
        f"/{test_user_id}",
        json={"action_type": "deactivate"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200

    mocked_asyncpg_con.execute.assert_called_once_with(
        "UPDATE users SET suspended='t' WHERE id=$1 AND customer_id=$2", test_user_id, test_customer_id
    )


def test_user_id__put__successful_reactivation(mocked_asyncpg_con):
    test_customer_id = uuid.uuid4()
    access_token = get_token(customer_id=test_customer_id, account_type=AccountTypes.ADMIN)

    test_user_id = uuid.uuid4()

    response = test_client.put(
        f"/{test_user_id}",
        json={"action_type": "reactivate"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200

    mocked_asyncpg_con.execute.assert_called_once_with(
        "UPDATE users SET suspended='f', failed_login_attempts=0 WHERE id=$1 AND customer_id=$2",
        test_user_id,
        test_customer_id,
    )


def test_account_id__put__successful_customer_alias_update(mocked_asyncpg_con):
    test_customer_id = uuid.uuid4()
    access_token = get_token(customer_id=test_customer_id, account_type=AccountTypes.ADMIN)

    test_alias = "test_alias"

    response = test_client.put(
        f"/{test_customer_id}",
        json={"action_type": "set_alias", "new_alias": test_alias},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200

    mocked_asyncpg_con.execute.assert_called_once_with(
        "UPDATE customers SET alias=LOWER($1) WHERE id=$2", test_alias, test_customer_id
    )


def test_account_id__put__admin_edit_self_with_mismatched_account_ids(mocked_asyncpg_con):
    access_token = get_token(account_type=AccountTypes.ADMIN)

    response = test_client.put(
        f"/{uuid.uuid4()}",
        # arbitrarily choosing set_alias here
        json={"action_type": "set_alias", "new_alias": "test_alias"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 400

    mocked_asyncpg_con.assert_not_called()


def test_account_id__put__user_edit_self_with_mismatched_account_ids(mocked_asyncpg_con):
    access_token = get_token(account_type=AccountTypes.USER)

    other_id = uuid.uuid4()

    response = test_client.put(
        f"/{other_id}", json={"action_type": "any"}, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 400

    mocked_asyncpg_con.assert_not_called()


def test_account_id__put__invalid_action_type_given():
    access_token = get_token(account_type=AccountTypes.ADMIN)

    response = test_client.put(
        f"/{uuid.uuid4()}", json={"action_type": "bad"}, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 400


def test_account_id__put__no_action_type_given():
    access_token = get_token(account_type=AccountTypes.ADMIN)

    response = test_client.put(f"/{uuid.uuid4()}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 422


@pytest.mark.parametrize("method", ["PUT", "GET"])
def test_account_id__bad_user_id_given(method):
    access_token = get_token(account_type=AccountTypes.ADMIN)

    response = getattr(test_client, method.lower())(
        "/not_a_uuid", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 422


@pytest.mark.parametrize("test_token_scope", [[s] for s in ACCOUNT_SCOPES if "admin" not in s])
def test_account__put__user_account_is_already_verified(test_token_scope, mocked_asyncpg_con):
    test_account_id = uuid.uuid4()
    account_type = AccountTypes.USER

    access_token = get_token(scopes=test_token_scope, account_type=account_type, userid=test_account_id)

    mocked_asyncpg_con.fetchrow.return_value = {"verified": True}

    response = test_client.put(
        "/account",
        json={"password1": "Test_password1", "password2": "Test_password1", "verify": True},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert (
        response.json()
        == UnableToUpdateAccountResponse(message="Account has already been verified").model_dump()
    )


@pytest.mark.parametrize("test_token_scope", [[s] for s in ACCOUNT_SCOPES])
def test_account__put__link_has_already_been_used(test_token_scope, mocked_asyncpg_con):
    account_type = AccountTypes.USER if "user" in test_token_scope[0] else AccountTypes.ADMIN
    test_user_id = uuid.uuid4() if account_type == AccountTypes.USER else None
    test_customer_id = uuid.uuid4()
    access_token = get_token(
        scopes=test_token_scope, account_type=account_type, userid=test_user_id, customer_id=test_customer_id
    )

    mocked_asyncpg_con.fetchrow.return_value = {"verified": True, "reset_token": None}

    response = test_client.put(
        "/account",
        json={"password1": "Test_password1", "password2": "Test_password1", "verify": False},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.json() == UnableToUpdateAccountResponse(message="Link has already been used").model_dump()


@pytest.mark.parametrize("test_token_scope", [[s] for s in ACCOUNT_SCOPES])
def test_account__put__repeat_password(test_token_scope, mocked_asyncpg_con):
    account_type = AccountTypes.USER if "user" in test_token_scope[0] else AccountTypes.ADMIN
    test_user_id = uuid.uuid4() if account_type == AccountTypes.USER else None
    test_customer_id = uuid.uuid4()
    access_token = get_token(
        scopes=test_token_scope, account_type=account_type, userid=test_user_id, customer_id=test_customer_id
    )

    test_password = "Test_password1"

    ph = PasswordHasher()

    mocked_asyncpg_con.fetchrow.return_value = {
        "verified": True,
        "reset_token": access_token,
        "previous_passwords": [ph.hash("other_pw1"), ph.hash(test_password)],
    }

    response = test_client.put(
        "/account",
        json={"password1": test_password, "password2": test_password, "verify": False},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert (
        response.json()
        == UnableToUpdateAccountResponse(
            message="Cannot set password to any of the previous 5 passwords"
        ).model_dump()
    )


@pytest.mark.parametrize("test_token_scope", [[s] for s in ACCOUNT_SCOPES])
@pytest.mark.parametrize("test_reset_token", ["not a token", get_token()])
def test_account__put__token_does_not_match_reset_token(
    test_token_scope, test_reset_token, mocked_asyncpg_con
):
    account_type = AccountTypes.USER if "user" in test_token_scope[0] else AccountTypes.ADMIN
    test_user_id = uuid.uuid4() if account_type == AccountTypes.USER else None
    test_customer_id = uuid.uuid4()
    access_token = get_token(
        scopes=test_token_scope, account_type=account_type, userid=test_user_id, customer_id=test_customer_id
    )

    mocked_asyncpg_con.fetchrow.return_value = {"verified": True, "reset_token": test_reset_token}

    response = test_client.put(
        "/account",
        json={"password1": "Test_password1", "password2": "Test_password1", "verify": False},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.json() == UnableToUpdateAccountResponse(message="Link has expired").model_dump()


@pytest.mark.parametrize("test_token_scope", [[s] for s in ACCOUNT_SCOPES if "admin" in s])
def test_account__put__correctly_updates_customers_table_with_account_info(
    test_token_scope, mocked_asyncpg_con, spied_pw_hasher
):
    test_account_id = uuid.uuid4()
    account_type = AccountTypes.ADMIN
    access_token = get_token(scopes=test_token_scope, account_type=account_type, customer_id=test_account_id)

    ph = PasswordHasher()
    mocked_asyncpg_con.fetchrow.return_value = {
        "previous_passwords": [ph.hash("other_pw1"), ph.hash("other_pw1")],
        "reset_token": access_token,
    }

    response = test_client.put(
        "/account",
        json={"password1": "Test_password1", "password2": "Test_password1"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert not response.json()
    mocked_asyncpg_con.execute.assert_called_once_with(
        "UPDATE customers SET reset_token=NULL, password=$1, previous_passwords=array_prepend($1, previous_passwords[0:4]) WHERE id=$2",
        spied_pw_hasher.spy_return,
        test_account_id,
    )


@pytest.mark.parametrize("test_token_scope", [[s] for s in ACCOUNT_SCOPES if "admin" not in s])
def test_account__put__correctly_updates_users_table_with_account_info(
    test_token_scope, mocked_asyncpg_con, spied_pw_hasher
):
    test_account_id = uuid.uuid4()
    account_type = AccountTypes.USER
    test_customer_id = uuid.uuid4()
    access_token = get_token(
        scopes=test_token_scope,
        account_type=account_type,
        userid=test_account_id,
        customer_id=test_customer_id,
    )

    ph = PasswordHasher()
    mocked_asyncpg_con.fetchrow.return_value = {
        "verified": True,
        "previous_passwords": [ph.hash("other_pw1"), ph.hash("other_pw1")],
        "reset_token": access_token,
    }

    response = test_client.put(
        "/account",
        json={"password1": "Test_password1", "password2": "Test_password1", "verify": False},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert not response.json()
    mocked_asyncpg_con.execute.assert_called_once_with(
        "UPDATE users SET verified='t', reset_token=NULL, password=$1, previous_passwords=array_prepend($1, previous_passwords[0:4]) WHERE id=$2 AND customer_id=$3",
        spied_pw_hasher.spy_return,
        test_account_id,
        test_customer_id,
    )


@pytest.mark.parametrize("type", ["verify", "reset"])
def test_email__get__send_correct_email_based_on_request_query_type(mocked_asyncpg_con, mocker, type):
    mocked_send_account_email = mocker.patch.object(main, "_send_account_email", autospec=True)
    spied_create_token = mocker.spy(main, "create_token")
    test_user_email = "test_user@curibio.com"
    test_customer_id = uuid.uuid4()
    test_user_id = uuid.uuid4()
    test_username = "test_user"

    mocked_asyncpg_con.fetchrow.return_value = {
        "id": test_user_id,
        "customer_id": test_customer_id,
        "name": test_username,
    }

    response = test_client.get(f"/email?email={test_user_email}&type={type}&user=true")

    assert response.status_code == 204

    mocked_asyncpg_con.execute.assert_called_once_with(
        "UPDATE users SET reset_token=$1 WHERE id=$2", spied_create_token.spy_return.token, test_user_id
    )

    if type == "reset":
        subject = "Reset your password"
        template = "reset_password.html"
    elif type == "verify":
        subject = "Please verify your email address"
        template = "registration.html"

    mocked_send_account_email.assert_called_once_with(
        username=test_username,
        email=test_user_email,
        url=f"https://dashboard.curibio-test.com/account/{type}?token={spied_create_token.spy_return.token}",
        subject=subject,
        template=template,
    )


@pytest.mark.parametrize("type", ["verify", "reset"])
def test_email__get__returns_204_when_email_is_not_found(mocked_asyncpg_con, mocker, type):
    spied_create_email = mocker.spy(main, "_create_account_email")
    test_user_email = "test_user@curibio.com"
    mocked_asyncpg_con.fetchrow.return_value = None

    response = test_client.get(f"/email?email={test_user_email}&type={type}")

    assert response.status_code == 204
    spied_create_email.assert_not_called()


def test_email__get__returns_exception_if_unknown_type_is_used(mocked_asyncpg_con, mocker):
    mocked_send_account_email = mocker.patch.object(main, "_send_account_email", autospec=True)
    test_user_email = "test_user@curibio.com"
    test_customer_id = uuid.uuid4()
    test_user_id = uuid.uuid4()
    test_username = "test_user"
    unknown_type = "other"

    mocked_asyncpg_con.fetchrow.return_value = {
        "id": test_user_id,
        "customer_id": test_customer_id,
        "name": test_username,
    }

    response = test_client.get(f"/email?email={test_user_email}&type={unknown_type}&user=true")

    assert response.status_code == 500

    mocked_asyncpg_con.execute.assert_not_called()
    mocked_send_account_email.assert_not_called()
