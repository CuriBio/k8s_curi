import json
import uuid

from asyncpg.exceptions import UniqueViolationError
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
import pytest

from auth import create_token
from src import main
from src.models.tokens import LoginResponse

test_client = TestClient(main.app)


def get_token(scope, userid=None, refresh=False):
    if not userid:
        userid = uuid.uuid4()
    return create_token(scope=scope, userid=userid, refresh=refresh).token


@pytest.fixture(scope="function", name="cb_customer_id")
def fixture_cb_customer_id(mocker):
    cb_customer_id = uuid.uuid4()
    # patch this and create new attr since startup event is not invoked in most tests
    mocker.patch.object(main, "CB_CUSTOMER_ID", cb_customer_id, create=True)
    yield cb_customer_id


@pytest.fixture(scope="function", name="mocked_db_con", autouse=True)
async def fixture_mocked_db(mocker):
    mocked_db = mocker.patch.object(main, "db", autospec=True)
    mocked_db.pool = mocker.MagicMock()

    mocked_db_con = await mocked_db.pool.acquire().__aenter__()
    mocked_db_con.transaction = mocker.MagicMock()

    yield mocked_db_con


@pytest.fixture(scope="function", name="spied_pw_hasher")
def fixture_spied_pw_hasher(mocker):
    spied_pw_hasher = mocker.spy(main.PasswordHasher, "hash")
    yield spied_pw_hasher


def test_startup__sets_global_cb_customer_id(mocked_db_con):
    mocked_create_pool = main.db.create_pool

    test_id = uuid.uuid4()
    mocked_db_con.fetchval.return_value = test_id

    try:
        # using test_client in a with statement invokes startup event
        with test_client:
            assert main.CB_CUSTOMER_ID == test_id
    finally:
        # if test was successful, need to delete this attr so it doesn't leak into other tests
        if hasattr(main, "CB_CUSTOMER_ID"):
            del main.CB_CUSTOMER_ID

    mocked_db_con.fetchval.assert_called_once_with(
        "SELECT id FROM customers WHERE email = 'software@curibio.com'"
    )

    mocked_create_pool.assert_called_once()
    mocked_create_pool.assert_awaited_once()


def test_login__user__success(cb_customer_id, mocked_db_con, mocker):
    login_details = {
        "customer_id": str(cb_customer_id),
        "username": "test_username",
        "password": "test_password",
    }
    pw_hash = PasswordHasher().hash(login_details["password"])
    test_user_id = uuid.uuid4()
    test_scope = ["test:scope"]

    mocked_db_con.fetchrow.return_value = {
        "password": pw_hash,
        "id": test_user_id,
        "scope": json.dumps(test_scope),
    }
    spied_create_token = mocker.spy(main, "create_token")

    response = test_client.post("/login", json=login_details)
    assert response.status_code == 200
    assert response.json() == LoginResponse(
        access=create_token(scope=test_scope, userid=test_user_id, refresh=False),
        refresh=create_token(scope=test_scope, userid=test_user_id, refresh=True),
    )

    mocked_db_con.fetchrow.assert_called_once_with(
        "SELECT password, id, data->'scope' AS scope FROM users WHERE deleted_at IS NULL AND name = $1 AND customer_id = $2",
        login_details["username"],
        login_details["customer_id"],
    )

    assert spied_create_token.call_count == 2


def test_login__customer__success(mocked_db_con, mocker):
    login_details = {"username": "test_username", "password": "test_password"}
    pw_hash = PasswordHasher().hash(login_details["password"])
    test_customer_id = uuid.uuid4()

    mocked_db_con.fetchrow.return_value = {"password": pw_hash, "id": test_customer_id}
    spied_create_token = mocker.spy(main, "create_token")

    response = test_client.post("/login", json=login_details)
    assert response.status_code == 200
    assert response.json() == LoginResponse(
        access=create_token(scope=["users:admin"], userid=test_customer_id, refresh=False),
        refresh=create_token(scope=["users:admin"], userid=test_customer_id, refresh=True),
    )

    mocked_db_con.fetchrow.assert_called_once_with(
        "SELECT password, id, data->'scope' AS scope FROM customers WHERE deleted_at IS NULL AND email = $1",
        login_details["username"],
    )

    assert spied_create_token.call_count == 2


def test_login__no_matching_record_in_db(mocked_db_con):
    # arbitrarily deciding to use customer login here
    login_details = {"username": "test_username", "password": "test_password"}

    mocked_db_con.fetchrow.return_value = None

    response = test_client.post("/login", json=login_details)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


def test_login__incorrect_password(mocked_db_con):
    # arbitrarily deciding to use customer login here
    login_details = {"username": "test_username", "password": "test_password"}

    mocked_db_con.fetchrow.return_value = {"password": "bad_hash", "id": uuid.uuid4()}

    response = test_client.post("/login", json=login_details)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


@pytest.mark.parametrize("use_cb_customer_id", [True, False])
def test_register__user__success(use_cb_customer_id, mocked_db_con, spied_pw_hasher, cb_customer_id, mocker):
    registration_details = {
        "email": "test@email.com",
        "username": "testusername",
        "password1": "Testpw1234",
        "password2": "Testpw1234",
    }

    test_user_id = uuid.uuid4()
    test_customer_id = cb_customer_id if use_cb_customer_id else uuid.uuid4()
    access_token = get_token(scope=["users:admin"], userid=test_customer_id)

    mocked_db_con.fetchval.return_value = test_user_id

    expected_scope = ["users:free"]

    response = test_client.post(
        "/register", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 201
    assert response.json() == {
        "username": registration_details["username"],
        "email": registration_details["email"],
        "user_id": test_user_id.hex,
        "account_type": "free",
        "scope": expected_scope,
    }

    mocked_db_con.fetchval.assert_called_once_with(
        "INSERT INTO users (name, email, password, account_type, data, customer_id) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id",
        registration_details["username"],
        registration_details["email"],
        spied_pw_hasher.spy_return,
        "free",
        json.dumps({"scope": expected_scope}),
        test_customer_id,
    )
    spied_pw_hasher.assert_called_once_with(mocker.ANY, registration_details["password1"])


def test_register__customer__success(mocked_db_con, spied_pw_hasher, cb_customer_id, mocker):
    registration_details = {
        "email": "test@email.com",
        "password1": "Testpw1234",
        "password2": "Testpw1234",
    }

    test_user_id = uuid.uuid4()
    access_token = get_token(scope=["users:admin"], userid=cb_customer_id)

    mocked_db_con.fetchval.return_value = test_user_id

    expected_scope = ["users:admin"]

    response = test_client.post(
        "/register", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 201
    assert response.json() == {
        "email": registration_details["email"],
        "user_id": test_user_id.hex,
        "scope": expected_scope,
    }

    mocked_db_con.fetchval.assert_called_once_with(
        "INSERT INTO customers (email, password) VALUES ($1, $2) RETURNING id",
        registration_details["email"],
        spied_pw_hasher.spy_return,
    )
    spied_pw_hasher.assert_called_once_with(mocker.ANY, registration_details["password1"])


@pytest.mark.parametrize(
    "contraint_to_violate,expected_error_message",
    [
        ("users_customer_id_name_key", "Username already in use"),
        ("users_email_key", "Account registration failed"),
        ("all others", "Account registration failed"),
    ],
)
def test_register__user__unique_constraint_violations(
    contraint_to_violate, expected_error_message, mocked_db_con, spied_pw_hasher, cb_customer_id, mocker
):
    registration_details = {
        "email": "test@email.com",
        "username": "testusername",
        "password1": "Testpw1234",
        "password2": "Testpw1234",
    }

    test_user_id = uuid.uuid4()
    access_token = get_token(scope=["users:admin"], userid=test_user_id)

    # setting this
    mocked_db_con.fetchval.side_effect = UniqueViolationError(contraint_to_violate)

    response = test_client.post(
        "/register", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": expected_error_message}

    # make sure the pw was still hashed
    spied_pw_hasher.assert_called_once_with(mocker.ANY, registration_details["password1"])


@pytest.mark.parametrize(
    "contraint_to_violate,expected_error_message",
    [
        ("customers_email_key", "Email already in use"),
        ("all others", "Account registration failed"),
    ],
)
def test_register__user__unique_constraint_violations(
    contraint_to_violate, expected_error_message, mocked_db_con, spied_pw_hasher, cb_customer_id, mocker
):
    registration_details = {
        "email": "test@email.com",
        "password1": "Testpw1234",
        "password2": "Testpw1234",
    }

    access_token = get_token(scope=["users:admin"], userid=cb_customer_id)

    # setting this
    mocked_db_con.fetchval.side_effect = UniqueViolationError(contraint_to_violate)

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
    access_token = get_token(scope=["users:free"])
    response = test_client.post(
        "/register", json=registration_details, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 401


def test_register__no_token_given():
    # arbitrarily deciding to use customer login here
    registration_details = {"email": "user@new.com", "password1": "pw", "password2": "pw"}
    response = test_client.post("/register", json=registration_details)
    assert response.status_code == 403
