import os
import pytest

VALID_CUSTOMER_ID = os.getenv("VALID_USER_ID")
VALID_USER_NAME = os.getenv("VALID_USER_NAME")
VALID_USER_PASSWORD = os.getenv("VALID_USER_PASSWORD")
TEST_URL = os.getenv("TEST_URL")


def test_login_succes(page):
    page.goto(f"{TEST_URL}/login")
    page.wait_for_load_state("networkidle")
    page.reload()

    # click to select login form for user
    page.click("text=User")

    # get input fields
    customerIdInput = page.get_by_placeholder("CuriBio")
    userNameInput = page.get_by_placeholder("user")
    passwordInput = page.get_by_placeholder("Password")

    # check correct input form displayed
    assert customerIdInput.is_visible()
    assert userNameInput.is_visible()
    assert passwordInput.is_visible()

    # populate form with valid credentials
    customerIdInput.fill(VALID_CUSTOMER_ID)
    userNameInput.fill(VALID_USER_NAME)
    passwordInput.fill(VALID_USER_PASSWORD)

    # submit form
    page.click("text=Submit")
    page.wait_for_url("**/uploads")

    # check that the login was successful
    assert page.url == f"http://{TEST_URL}/uploads"
    page.close()


invalidUsers = [
    (
        "*Invalid credentials. Try again.",
        {"customerId": "1", "username": VALID_USER_NAME, "password": VALID_USER_PASSWORD},
    ),
    (
        "*Invalid credentials. Try again.",
        {"customerId": VALID_CUSTOMER_ID, "username": "InvalidUser", "password": VALID_USER_PASSWORD},
    ),
    (
        "*Invalid credentials. Try again.",
        {"customerId": VALID_CUSTOMER_ID, "username": VALID_USER_NAME, "password": "InvalidPassword"},
    ),
]


@pytest.mark.parametrize("ExpectedMessage, InvalidInputs", invalidUsers)
def test_invalid_inputs(page, ExpectedMessage, InvalidInputs):
    page.goto(f"{TEST_URL}/login")
    page.wait_for_load_state("networkidle")
    page.reload()

    # click to select login form for user
    page.click("text=User")

    # get input fields
    customerIdInput = page.get_by_placeholder("CuriBio")
    userNameInput = page.get_by_placeholder("user")
    passwordInput = page.get_by_placeholder("Password")

    # check correct input form displayed
    assert customerIdInput.is_visible()
    assert userNameInput.is_visible()
    assert passwordInput.is_visible()

    # populate form with valid credentials
    customerIdInput.fill(InvalidInputs["customerId"])
    userNameInput.fill(InvalidInputs["username"])
    passwordInput.fill(InvalidInputs["password"])

    # submit form
    page.click("text=Submit")
    page.wait_for_load_state("networkidle")

    # check correct error message displayed
    assert page.locator("#loginError").inner_text() == ExpectedMessage
    page.close()
