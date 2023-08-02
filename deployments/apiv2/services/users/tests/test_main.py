from datetime import datetime, timedelta
import json
from random import choice, randint
import uuid

from argon2 import PasswordHasher
from asyncpg.exceptions import UniqueViolationError
from fastapi.testclient import TestClient
from freezegun import freeze_time
import pytest

from auth import create_token, ACCOUNT_SCOPES, PULSE3D_PAID_USAGE
from auth.settings import REFRESH_TOKEN_EXPIRE_MINUTES
from src import main
from src.models.tokens import AuthTokens
from src.models.users import (
    USERNAME_MIN_LEN,
    USERNAME_MAX_LEN,
    USERNAME_VALID_SPECIAL_CHARS,
    LoginResponse,
    UnableToUpdateAccountResponse,
)

test_client = TestClient(main.app)


TEST_PASSWORD = "Testpw123!"


def get_token(*, userid=None, customer_id=None, scope=None, account_type=None, refresh=False):
    if not userid:
        userid = uuid.uuid4()
    if not account_type:
        account_type = choice(["user", "customer"])
    if not customer_id and account_type == "user":
        customer_id = uuid.uuid4()
    if not scope:
        scope = ["pulse3d:free"] if account_type == "user" else ["customer:paid"]

    return create_token(
        userid=userid, customer_id=customer_id, scope=scope, account_type=account_type, refresh=refresh
    ).token


@pytest.fixture(scope="function", name="cb_customer_id")
def fixture_cb_customer_id(mocker):
    cb_customer_id = uuid.uuid4()
    # patch this and create new attr since startup event is not invoked in most tests
    mocker.patch.object(main, "CB_CUSTOMER_ID", cb_customer_id, create=True)
    yield cb_customer_id


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


def test_startup__sets_global_cb_customer_id(mocked_asyncpg_con):
    test_id = uuid.uuid4()
    mocked_asyncpg_con.fetchval.return_value = test_id

    try:
        # using test_client in a with statement invokes startup event
        with test_client:
            assert main.CB_CUSTOMER_ID == test_id
    finally:
        # if test was successful, need to delete this attr so it doesn't leak into other tests
        if hasattr(main, "CB_CUSTOMER_ID"):
            del main.CB_CUSTOMER_ID

    mocked_asyncpg_con.fetchval.assert_called_once_with(
        "SELECT id FROM customers WHERE email='software@curibio.com'"
    )


@pytest.mark.parametrize(
    "method,route",
    [
        ("POST", "/register"),
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
def test_login__user__success(send_client_type, use_alias, cb_customer_id, mocked_asyncpg_con, mocker):
    mocked_usage_check = mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={
            "current": {
                "uploads": "0",
                "jobs": "0",
            },
            "jobs_reached": False,
            "limits": {"expiration_date": "", "jobs": "-1", "uploads": "-1"},
            "uploads_reached": False,
        },
        autospec=True,
    )

    login_details = {
        "customer_id": "test_alias" if use_alias else str(cb_customer_id),
        "username": "test_USERNAME",
        "password": "test_password",
        "service": "pulse3d",
    }
    if send_client_type:
        login_details["client_type"] = "dashboard"

    pw_hash = PasswordHasher().hash(login_details["password"])
    test_user_id = uuid.uuid4()
    test_scope = ["test:scope"]

    mocked_asyncpg_con.fetchrow.return_value = {
        "password": pw_hash,
        "id": test_user_id,
        "scope": json.dumps(test_scope),
        "customer_id": cb_customer_id,
    }
    spied_create_token = mocker.spy(main, "create_token")

    expected_access_token = create_token(
        userid=test_user_id, customer_id=cb_customer_id, scope=test_scope, account_type="user", refresh=False
    )
    expected_refresh_token = create_token(
        userid=test_user_id, customer_id=cb_customer_id, scope=test_scope, account_type="user", refresh=True
    )

    response = test_client.post("/login", json=login_details)
    assert response.status_code == 200

    assert response.json() == LoginResponse(
        tokens=AuthTokens(access=expected_access_token, refresh=expected_refresh_token),
        usage_quota=mocked_usage_check.return_value,
    )

    expected_query = (
        "SELECT u.password, u.id, u.data->'scope' AS scope, u.customer_id FROM users AS u JOIN customers AS c ON u.customer_id=c.id WHERE u.deleted_at IS NULL AND u.name=$1 AND c.alias=$2 AND u.suspended='f' AND u.verified='t'"
        if use_alias
        else "SELECT password, id, data->'scope' AS scope, customer_id FROM users WHERE deleted_at IS NULL AND name=$1 AND customer_id=$2 AND suspended='f' AND verified='t'"
    )

    mocked_asyncpg_con.fetchrow.assert_called_once_with(
        expected_query, login_details["username"].lower(), login_details["customer_id"]
    )
    mocked_asyncpg_con.execute.assert_called_with(
        "UPDATE users SET refresh_token=$1 WHERE id=$2", expected_refresh_token.token, test_user_id
    )

    assert spied_create_token.call_count == 2


@freeze_time()
@pytest.mark.parametrize("send_client_type", [True, False])
def test_login__customer__success(send_client_type, mocked_asyncpg_con, mocker):
    mocked_usage_check = mocker.patch.object(
        main,
        "check_customer_quota",
        return_value={
            "current": {
                "uploads": "0",
                "jobs": "0",
            },
            "jobs_reached": False,
            "limits": {"expiration_date": "", "jobs": "-1", "uploads": "-1"},
            "uploads_reached": False,
        },
        asutospec=True,
    )

    login_details = {"email": "TEST@email.com", "password": "test_password", "service": "pulse3d"}
    if send_client_type:
        login_details["client_type"] = "dashboard"

    pw_hash = PasswordHasher().hash(login_details["password"])
    test_customer_id = uuid.uuid4()
    customer_scope = ["pulse3d:free"]

    mocked_asyncpg_con.fetchrow.return_value = {
        "password": pw_hash,
        "id": test_customer_id,
        "scope": json.dumps(customer_scope),
    }
    spied_create_token = mocker.spy(main, "create_token")

    expected_access_token = create_token(
        userid=test_customer_id,
        customer_id=None,
        scope=["customer:free"],
        account_type="customer",
        refresh=False,
    )
    expected_refresh_token = create_token(
        userid=test_customer_id,
        customer_id=None,
        scope=["customer:free"],
        account_type="customer",
        refresh=True,
    )

    response = test_client.post("/login", json=login_details)
    assert response.status_code == 200
    assert response.json() == LoginResponse(
        tokens=AuthTokens(access=expected_access_token, refresh=expected_refresh_token),
        usage_quota=mocked_usage_check.return_value,
    )

    mocked_asyncpg_con.fetchrow.assert_called_once_with(
        "SELECT password, id, data->'scope' AS scope FROM customers WHERE deleted_at IS NULL AND email=$1",
        login_details["email"].lower(),
    )
    mocked_asyncpg_con.execute.assert_called_with(
        "UPDATE customers SET refresh_token=$1 WHERE id=$2",
        expected_refresh_token.token,
        test_customer_id,
    )

    assert spied_create_token.call_count == 2


def test_login__no_matching_record_in_db(mocked_asyncpg_con):
    # arbitrarily deciding to use customer login here
    login_details = {"email": "test@email.com", "password": "test_password", "service": "pulse3d"}

    mocked_asyncpg_con.fetchrow.return_value = None

    response = test_client.post("/login", json=login_details)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


def test_login__incorrect_password(mocked_asyncpg_con):
    # arbitrarily deciding to use customer login here
    login_details = {"email": "test@email.com", "password": "test_password", "service": "pulse3d"}

    mocked_asyncpg_con.fetchrow.return_value = {"password": "bad_hash", "id": uuid.uuid4()}

    response = test_client.post("/login", json=login_details)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


@pytest.mark.parametrize("special_char", ["", *USERNAME_VALID_SPECIAL_CHARS])
def test_register__user__allows_valid_usernames(special_char, mocked_asyncpg_con, cb_customer_id, mocker):
    mocker.patch.object(main, "_send_user_email", autospec=True)
    use_cb_customer_id = choice([True, False])
    end_with_num = choice([True, False])

    registration_details = {
        "email": "USEr@example.com",
        "username": f"Test{special_char}UseRName",
        "service": "pulse3d",
    }

    if end_with_num:
        registration_details["username"] += str(randint(0, 9))

    test_user_id = uuid.uuid4()
    test_customer_id = cb_customer_id if use_cb_customer_id else uuid.uuid4()
    access_token = get_token(userid=test_customer_id, scope=["customer:paid"], account_type="customer")

    mocked_asyncpg_con.fetchval.return_value = test_user_id
    expected_scope = ["pulse3d:paid"]

    response = test_client.post(
        "/register", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 201
    assert response.json() == {
        "username": registration_details["username"].lower(),
        "email": registration_details["email"].lower(),
        "user_id": test_user_id.hex,
        "account_type": "paid",
        "scope": expected_scope,
    }

    mocked_asyncpg_con.fetchval.assert_called_once_with(
        "INSERT INTO users (name, email, account_type, data, customer_id) VALUES ($1, $2, $3, $4, $5) RETURNING id",
        registration_details["username"].lower(),
        registration_details["email"].lower(),
        "paid",
        json.dumps({"scope": expected_scope}),
        test_customer_id,
    )


def test_register__customer__success(mocked_asyncpg_con, spied_pw_hasher, cb_customer_id, mocker):
    registration_details = {
        "email": "tEsT@email.com",
        "password1": TEST_PASSWORD,
        "password2": TEST_PASSWORD,
        "scope": ["customer:paid"],
    }

    test_user_id = uuid.uuid4()
    expected_scope = ["customer:paid"]
    access_token = get_token(userid=cb_customer_id, scope=expected_scope, account_type="customer")

    mocked_asyncpg_con.fetchval.return_value = test_user_id

    response = test_client.post(
        "/register", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 201
    assert response.json() == {
        "email": registration_details["email"].lower(),
        "user_id": test_user_id.hex,
        "scope": expected_scope,
    }

    mocked_asyncpg_con.fetchval.assert_called_once_with(
        "INSERT INTO customers (email, password, previous_passwords, data, usage_restrictions) VALUES ($1, $2, ARRAY[$3], $4, $5) RETURNING id",
        registration_details["email"].lower(),
        spied_pw_hasher.spy_return,
        spied_pw_hasher.spy_return,
        json.dumps({"scope": expected_scope}),
        json.dumps(dict(PULSE3D_PAID_USAGE)),
    )
    spied_pw_hasher.assert_called_once_with(mocker.ANY, registration_details["password1"])


@pytest.mark.parametrize(
    "length,err_msg",
    [
        (USERNAME_MIN_LEN - 1, "Username does not meet min length"),
        (USERNAME_MAX_LEN + 1, "Username exceeds max length"),
    ],
)
def test_register__user__invalid_username_length(length, err_msg, cb_customer_id):
    registration_details = {
        "email": "test@email.com",
        "username": "a" * length,
        "password1": TEST_PASSWORD,
        "password2": TEST_PASSWORD,
        "service": "pulse3d",
    }

    access_token = get_token(userid=cb_customer_id, scope=["customer:paid"], account_type="customer")

    response = test_client.post(
        "/register", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 422
    assert response.json()["detail"][-1]["msg"] == err_msg


@pytest.mark.parametrize("special_char", ["@", "#", "$", "*", "&", "%"])
def test_register__user__with_invalid_char_in_username(special_char, cb_customer_id):
    registration_details = {
        "email": "test@email.com",
        "username": f"bad{special_char}username",
        "password1": TEST_PASSWORD,
        "password2": TEST_PASSWORD,
        "service": "pulse3d",
    }

    access_token = get_token(userid=cb_customer_id, scope=["customer:paid"], account_type="customer")

    response = test_client.post(
        "/register", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 422
    assert (
        response.json()["detail"][-1]["msg"]
        == f"Username can only contain letters, numbers, and these special characters: {USERNAME_VALID_SPECIAL_CHARS}"
    )


@pytest.mark.parametrize("bad_first_char", [*USERNAME_VALID_SPECIAL_CHARS, str(randint(0, 9))])
def test_register__user__with_invalid_first_char(bad_first_char, cb_customer_id):
    registration_details = {
        "email": "test@email.com",
        "username": f"{bad_first_char}username",
        "password1": TEST_PASSWORD,
        "password2": TEST_PASSWORD,
        "service": "pulse3d",
    }

    access_token = get_token(userid=cb_customer_id, scope=["customer:paid"], account_type="customer")

    response = test_client.post(
        "/register", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 422
    assert response.json()["detail"][-1]["msg"] == "Username must start with a letter"


@pytest.mark.parametrize("bad_final_char", USERNAME_VALID_SPECIAL_CHARS)
def test_register__user__with_invalid_final_char(bad_final_char, cb_customer_id):
    registration_details = {
        "email": "test@email.com",
        "username": f"username{bad_final_char}",
        "password1": TEST_PASSWORD,
        "password2": TEST_PASSWORD,
        "service": "pulse3d",
    }

    access_token = get_token(userid=cb_customer_id, scope=["customer:paid"], account_type="customer")

    response = test_client.post(
        "/register", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 422
    assert response.json()["detail"][-1]["msg"] == "Username must end with a letter or number"


@pytest.mark.parametrize("special_char", USERNAME_VALID_SPECIAL_CHARS)
def test_register__user__with_consecutive_special_chars(special_char, cb_customer_id):
    registration_details = {
        "email": "test@email.com",
        "username": f"a-{special_char}a",
        "password1": TEST_PASSWORD,
        "password2": TEST_PASSWORD,
        "service": "pulse3d",
    }

    access_token = get_token(userid=cb_customer_id, scope=["customer:paid"], account_type="customer")

    response = test_client.post(
        "/register", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 422
    assert response.json()["detail"][-1]["msg"] == "Username cannot contain consecutive special characters"


@pytest.mark.parametrize(
    "contraint_to_violate,expected_error_message",
    [
        ("users_customer_id_name_key", "Username already in use"),
        ("users_email_key", "Email already in use"),
        ("all others", "Account registration failed"),
    ],
)
def test_register__user__unique_constraint_violations(
    contraint_to_violate, expected_error_message, mocked_asyncpg_con, cb_customer_id
):
    registration_details = {
        "email": "test@email.com",
        "username": "testusername",
        "service": "pulse3d",
    }

    test_user_id = uuid.uuid4()
    access_token = get_token(userid=test_user_id, scope=["customer:paid"], account_type="customer")

    mocked_asyncpg_con.fetchval.side_effect = UniqueViolationError(contraint_to_violate)

    response = test_client.post(
        "/register", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": expected_error_message}


@pytest.mark.parametrize(
    "contraint_to_violate,expected_error_message",
    [("customers_email_key", "Email already in use"), ("all others", "Account registration failed")],
)
def test_register__customer__unique_constraint_violations(
    contraint_to_violate, expected_error_message, mocked_asyncpg_con, spied_pw_hasher, cb_customer_id, mocker
):
    registration_details = {
        "email": "test@email.com",
        "password1": TEST_PASSWORD,
        "password2": TEST_PASSWORD,
        "scope": ["customer:paid"],
    }

    access_token = get_token(userid=cb_customer_id, scope=["customer:paid"], account_type="customer")

    # setting this
    mocked_asyncpg_con.fetchval.side_effect = UniqueViolationError(contraint_to_violate)

    response = test_client.post(
        "/register", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": expected_error_message}

    # make sure the pw was still hashed
    spied_pw_hasher.assert_called_once_with(mocker.ANY, registration_details["password1"])


def test_register__invalid_token_scope_given():
    # arbitrarily deciding to use customer login here
    registration_details = {"email": "user@new.com", "password1": "pw", "password2": "pw"}
    access_token = get_token(scope=["users:free"], account_type="customer")
    response = test_client.post(
        "/register", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 401


@freeze_time()
@pytest.mark.parametrize("account_type", ["user", "customer"])
def test_refresh__success(account_type, mocked_asyncpg_con):
    userid = uuid.uuid4()
    test_scope = ["users:free"]
    customer_id = None if account_type == "customer" else uuid.uuid4()

    select_clause = "refresh_token"
    if account_type == "user":
        select_clause += ", customer_id"

    old_refresh_token = get_token(
        userid=userid, customer_id=customer_id, scope=test_scope, account_type=account_type, refresh=True
    )

    new_access_token = create_token(
        userid=userid, customer_id=customer_id, scope=test_scope, account_type=account_type, refresh=False
    )
    new_refresh_token = create_token(
        userid=userid, customer_id=customer_id, scope=test_scope, account_type=account_type, refresh=True
    )

    mocked_asyncpg_con.fetchrow.return_value = {"refresh_token": old_refresh_token}
    if account_type == "user":
        mocked_asyncpg_con.fetchrow.return_value["customer_id"] = customer_id

    response = test_client.post("/refresh", headers={"Authorization": f"Bearer {old_refresh_token}"})
    assert response.status_code == 201
    assert response.json() == AuthTokens(access=new_access_token, refresh=new_refresh_token)

    mocked_asyncpg_con.fetchrow.assert_called_once_with(
        f"SELECT {select_clause} FROM {account_type}s WHERE id=$1", userid
    )
    mocked_asyncpg_con.execute.assert_called_once_with(
        f"UPDATE {account_type}s SET refresh_token=$1 WHERE id=$2", old_refresh_token, userid
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


@pytest.mark.parametrize("account_type", ["user", "customer"])
def test_logout__success(account_type, mocked_asyncpg_con):
    test_id = uuid.uuid4()
    access_token = get_token(userid=test_id, account_type=account_type)

    response = test_client.post("/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 204

    mocked_asyncpg_con.execute.assert_called_once_with(
        f"UPDATE {account_type}s SET refresh_token = NULL WHERE id = $1", test_id
    )


def test_account_id__get__no_id(mocked_asyncpg_con):
    test_customer_id = uuid.uuid4()
    access_token = get_token(userid=test_customer_id, account_type="customer")

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
        f"SELECT {', '.join(expected_users_info[0])} FROM users WHERE customer_id=$1 AND deleted_at IS NULL ORDER BY suspended",
        test_customer_id,
    )


def test_account_id__get__no_id__invalid_token_scope_given():
    # account type does not matter here
    access_token = get_token(scope=["users:free"])
    response = test_client.get("/", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 401


def test_account_id__get__id_given__customer_retrieving_self(mocked_asyncpg_con):
    test_customer_id = uuid.uuid4()
    access_token = get_token(userid=test_customer_id, account_type="customer")

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
        f"SELECT {', '.join(expected_customer_info)} FROM customers WHERE id=$1",
        test_customer_id,
    )


def test_account_id__get__id_given__customer_retrieving_user__success(mocked_asyncpg_con):
    test_customer_id = uuid.uuid4()
    access_token = get_token(userid=test_customer_id, account_type="customer")

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


def test_account_id__get__id_given__customer_retrieving_user__user_not_found(mocked_asyncpg_con):
    test_customer_id = uuid.uuid4()
    access_token = get_token(userid=test_customer_id, account_type="customer")

    test_user_id = uuid.uuid4()

    mocked_asyncpg_con.fetchrow.return_value = None

    response = test_client.get(f"/{test_user_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 400


def test_account_id__get__id_given__user_retrieving_self(mocked_asyncpg_con):
    test_user_id = uuid.uuid4()
    test_customer_id = uuid.uuid4()
    access_token = get_token(userid=test_user_id, customer_id=test_customer_id, account_type="user")

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
    access_token = get_token(account_type="user")

    response = test_client.get(f"/{uuid.uuid4()}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 400


def test_account_id__get__id_given__user_not_found(mocked_asyncpg_con):
    access_token = get_token(account_type="customer")

    mocked_asyncpg_con.fetchrow.return_value = None

    response = test_client.get(f"/{uuid.uuid4()}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 400


@freeze_time()
def test_account_id__put__successful_user_deletion(mocked_asyncpg_con):
    test_customer_id = uuid.uuid4()
    access_token = get_token(userid=test_customer_id, account_type="customer")

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


@pytest.mark.parametrize("action", ["deactivate", "reactivate"])
def test_account_id__put__successful_update_to_user_activation_status(mocked_asyncpg_con, action):
    test_customer_id = uuid.uuid4()
    access_token = get_token(userid=test_customer_id, account_type="customer")

    test_user_id = uuid.uuid4()

    response = test_client.put(
        f"/{test_user_id}",
        json={"action_type": action},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200

    mocked_asyncpg_con.execute.assert_called_once_with(
        "UPDATE users SET suspended=$1 WHERE id=$2 AND customer_id=$3",
        action == "deactivate",
        test_user_id,
        test_customer_id,
    )


def test_account_id__put__successful_customer_alias_update(mocked_asyncpg_con):
    test_customer_id = uuid.uuid4()
    access_token = get_token(userid=test_customer_id, account_type="customer")

    test_alias = "test_alias"

    response = test_client.put(
        f"/{test_customer_id}",
        json={"action_type": "set_alias", "new_alias": test_alias},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200

    mocked_asyncpg_con.execute.assert_called_once_with(
        "UPDATE customers SET alias=$1 WHERE id=$2", test_alias, test_customer_id
    )


def test_account_id__put__customer_edit_self_with_mismatched_account_ids(mocked_asyncpg_con):
    access_token = get_token(account_type="customer")

    response = test_client.put(
        f"/{uuid.uuid4()}",
        # arbitrarily choosing set_alias here
        json={"action_type": "set_alias", "new_alias": "test_alias"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 400

    mocked_asyncpg_con.assert_not_called()


def test_account_id__put__user_edit_self_with_mismatched_account_ids(mocked_asyncpg_con):
    access_token = get_token(account_type="user")

    other_id = uuid.uuid4()

    response = test_client.put(
        f"/{other_id}",
        json={"action_type": "any"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 400

    mocked_asyncpg_con.assert_not_called()


def test_account_id__put__invalid_action_type_given():
    access_token = get_token(account_type="customer")

    response = test_client.put(
        f"/{uuid.uuid4()}", json={"action_type": "bad"}, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 400


def test_account_id__put__no_action_type_given():
    access_token = get_token(account_type="customer")

    response = test_client.put(f"/{uuid.uuid4()}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 422


@pytest.mark.parametrize("method", ["PUT", "GET"])
def test_account_id__bad_user_id_given(method):
    access_token = get_token(account_type="customer")

    response = getattr(test_client, method.lower())(
        "/not_a_uuid", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "test_token_scope",
    [[s] for s in ACCOUNT_SCOPES if "customer" not in s],
)
def test_account__put__account_is_already_verified(test_token_scope, mocked_asyncpg_con):
    test_account_id = uuid.uuid4()
    account_type = "user"

    access_token = get_token(
        scope=test_token_scope,
        account_type=account_type,
        userid=test_account_id,
    )

    mocked_asyncpg_con.fetchrow.return_value = {
        "verified": True,
    }

    response = test_client.put(
        "/account",
        json={"password1": "Test_password1", "password2": "Test_password1", "verify": True},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.json() == UnableToUpdateAccountResponse(message="Account has already been verified")


@pytest.mark.parametrize("test_token_scope", [[s] for s in ACCOUNT_SCOPES])
def test_account__put__link_has_already_been_used(test_token_scope, mocked_asyncpg_con):
    test_account_id = uuid.uuid4()
    account_type = "user" if "user" in test_token_scope[0] else "customer"
    test_customer_id = uuid.uuid4() if account_type == "user" else None
    access_token = get_token(
        scope=test_token_scope,
        account_type=account_type,
        userid=test_account_id,
        customer_id=test_customer_id,
    )

    mocked_asyncpg_con.fetchrow.return_value = {"verified": True, "reset_token": None}

    response = test_client.put(
        "/account",
        json={"password1": "Test_password1", "password2": "Test_password1", "verify": False},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.json() == UnableToUpdateAccountResponse(message="Link has already been used")


@pytest.mark.parametrize("test_token_scope", [[s] for s in ACCOUNT_SCOPES])
def test_account__put__repeat_password(test_token_scope, mocked_asyncpg_con):
    test_account_id = uuid.uuid4()
    account_type = "user" if "user" in test_token_scope[0] else "customer"
    test_customer_id = uuid.uuid4() if account_type == "user" else None
    access_token = get_token(
        scope=test_token_scope,
        account_type=account_type,
        userid=test_account_id,
        customer_id=test_customer_id,
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

    assert response.json() == UnableToUpdateAccountResponse(
        message="Cannot set password to any of the previous 5 passwords"
    )


@pytest.mark.parametrize("test_token_scope", [[s] for s in ACCOUNT_SCOPES])
@pytest.mark.parametrize("test_reset_token", ["not a token", get_token()])
def test_account__put__token_does_not_match_reset_token(
    test_token_scope, test_reset_token, mocked_asyncpg_con
):
    test_account_id = uuid.uuid4()
    account_type = "user" if "user" in test_token_scope[0] else "customer"
    test_customer_id = uuid.uuid4() if account_type == "user" else None
    access_token = get_token(
        scope=test_token_scope,
        account_type=account_type,
        userid=test_account_id,
        customer_id=test_customer_id,
    )

    mocked_asyncpg_con.fetchrow.return_value = {"verified": True, "reset_token": test_reset_token}

    response = test_client.put(
        "/account",
        json={"password1": "Test_password1", "password2": "Test_password1", "verify": False},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.json() == UnableToUpdateAccountResponse(message="Link has expired")


@pytest.mark.parametrize(
    "test_token_scope",
    [[s] for s in ACCOUNT_SCOPES if "customer" in s],
)
def test_account__put__correctly_updates_customers_table_with_account_info(
    test_token_scope, mocked_asyncpg_con, spied_pw_hasher
):
    test_account_id = uuid.uuid4()
    account_type = "customer"
    access_token = get_token(
        scope=test_token_scope,
        account_type=account_type,
        userid=test_account_id,
    )

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


@pytest.mark.parametrize(
    "test_token_scope",
    [[s] for s in ACCOUNT_SCOPES if "customer" not in s],
)
def test_account__put__correctly_updates_users_table_with_account_info(
    test_token_scope, mocked_asyncpg_con, spied_pw_hasher
):
    test_account_id = uuid.uuid4()
    account_type = "user"
    test_customer_id = uuid.uuid4()
    access_token = get_token(
        scope=test_token_scope,
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


@pytest.mark.parametrize("test_token_scope", [ACCOUNT_SCOPES, []])
def test_account__put__invalid_scopes(test_token_scope):
    access_token = get_token(scope=test_token_scope, account_type="customer")

    response = test_client.put(
        "/account",
        json={"password1": "Test_password1", "password2": "Test_password1", "verify": False},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 401


@pytest.mark.parametrize("type", ["verify", "reset"])
def test_email__get__send_correct_email_based_on_request_query_type(mocked_asyncpg_con, mocker, type):
    mocked_send_user_email = mocker.patch.object(main, "_send_user_email", autospec=True)
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
        "UPDATE users SET reset_token=$1 WHERE id=$2",
        spied_create_token.spy_return.token,
        test_user_id,
    )

    if type == "reset":
        subject = "Reset your password"
        template = "reset_password.html"
    elif type == "verify":
        subject = "Please verify your email address"
        template = "registration.html"

    mocked_send_user_email.assert_called_once_with(
        username=test_username,
        email=test_user_email,
        url=f"https://dashboard.curibio-test.com/account/{type}?token={spied_create_token.spy_return.token}",
        subject=subject,
        template=template,
    )


@pytest.mark.parametrize("type", ["verify", "reset"])
def test_email__get__returns_204_when_email_is_not_found(mocked_asyncpg_con, mocker, type):
    spied_create_email = mocker.spy(main, "_create_user_email")
    test_user_email = "test_user@curibio.com"
    mocked_asyncpg_con.fetchrow.return_value = None

    response = test_client.get(f"/email?email={test_user_email}&type={type}")

    assert response.status_code == 204
    spied_create_email.assert_not_called()


def test_email__get__returns_exception_if_unknown_type_is_used(mocked_asyncpg_con, mocker):
    mocked_send_user_email = mocker.patch.object(main, "_send_user_email", autospec=True)
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
    mocked_send_user_email.assert_not_called()
