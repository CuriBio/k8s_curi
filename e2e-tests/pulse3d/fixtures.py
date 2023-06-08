import pytest
from config import (
    TEST_URL,
    VALID_ADMIN_EMAIL,
    VALID_ADMIN_PASSWORD,
    VALID_CUSTOMER_ID,
    VALID_USER_NAME,
    VALID_USER_PASSWORD,
)


@pytest.fixture(autouse=True)
def loginAdmin(page):
    page.goto(f"{TEST_URL}/login")
    page.wait_for_load_state("networkidle")
    page.reload()
    page.click("text=Admin")

    # get input fields
    emailInput = page.get_by_placeholder("user@curibio.com")
    passwordInput = page.get_by_placeholder("Password")

    # check correct input form displayed
    assert emailInput.is_visible()
    assert passwordInput.is_visible()

    # populate form with valid credentials
    emailInput.fill(VALID_ADMIN_EMAIL)
    passwordInput.fill(VALID_ADMIN_PASSWORD)

    # submit form
    page.click("text=Submit")
    page.wait_for_url("**/uploads")

    # check that the login was successful
    assert page.url == f"http://{TEST_URL}/uploads"
    yield
    page.close()


@pytest.fixture(autouse=True)
def loginUser(page):
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
    yield
    page.close()
