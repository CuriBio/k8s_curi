import os
import pytest

VALID_ADMIN_EMAIL = os.getenv("VALID_ADMIN_EMAIL")
VALID_ADMIN_PASSWORD = os.getenv("VALID_ADMIN_PASSWORD")
TEST_URL = os.getenv("TEST_URL")


def test_login_succes(page):
    page.goto(f"{TEST_URL}/login")
    page.wait_for_load_state("networkidle")
    page.reload()

    # click to select login form for user
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
    page.close()


invalidAdmins = [
    ("*Invalid credentials. Try again.", {"adminEmail": "invalid@email.com", "password": VALID_ADMIN_EMAIL}),
    ("*Invalid credentials. Try again.", {"adminEmail": VALID_ADMIN_EMAIL, "password": "invalidPassword"}),
]


@pytest.mark.parametrize("ExpectedMessage, InvalidInputs", invalidAdmins)
def test_invalid_inputs(page, ExpectedMessage, InvalidInputs):
    page.goto(f"{TEST_URL}/login")
    page.wait_for_load_state("networkidle")
    page.reload()

    # click to select login form for user
    page.click("text=Admin")

    # get input fields
    emailInput = page.get_by_placeholder("user@curibio.com")
    passwordInput = page.get_by_placeholder("Password")

    # check correct input form displayed
    assert emailInput.is_visible()
    assert passwordInput.is_visible()

    # populate form with valid credentials
    emailInput.fill(InvalidInputs["customerId"])
    passwordInput.fill(InvalidInputs["username"])

    # submit form
    page.click("text=Submit")
    page.wait_for_load_state("networkidle")

    # check correct error message displayed
    assert page.locator("#loginError").inner_text() == ExpectedMessage
    page.close()
