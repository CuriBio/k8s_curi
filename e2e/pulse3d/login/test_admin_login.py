import pytest
from config import VALID_ADMIN_EMAIL, VALID_ADMIN_PASSWORD, TEST_URL
from fixtures import basic_page,setup,video_setup

@pytest.mark.asyncio
async def test_login_succes_admin(basic_page):
    # click to select login form for user
    await basic_page.click("text=Admin")

    # get input fields
    emailInput = basic_page.get_by_placeholder("user@curibio.com")
    passwordInput = basic_page.get_by_placeholder("Password")

    # check correct input form displayed
    assert await emailInput.is_visible()
    assert await passwordInput.is_visible()

    # populate form with valid credentials
    await emailInput.fill(VALID_ADMIN_EMAIL)
    await passwordInput.fill(VALID_ADMIN_PASSWORD)

    # submit form
    await basic_page.click("text=Submit")
    await basic_page.wait_for_url("**/uploads")

    # check that the login was successful
    assert basic_page.url == f"https://{TEST_URL}/uploads"


invalidAdmins = [
    ("*Invalid credentials. Try again.", {"adminEmail": "invalid@email.com", "password": VALID_ADMIN_EMAIL}),
    ("*Invalid credentials. Try again.", {"adminEmail": VALID_ADMIN_EMAIL, "password": "invalidPassword"}),
]
@pytest.mark.asyncio
@pytest.mark.parametrize("ExpectedMessage, InvalidInputs", invalidAdmins)
async def test_invalid_inputs_admin(basic_page, ExpectedMessage, InvalidInputs):
    # click to select login form for user
    await basic_page.click("text=Admin")

    # get input fields
    emailInput = basic_page.get_by_placeholder("user@curibio.com")
    passwordInput = basic_page.get_by_placeholder("Password")

    # check correct input form displayed
    assert await emailInput.is_visible()
    assert await passwordInput.is_visible()

    # populate form with invalid credentials
    await emailInput.fill(InvalidInputs["adminEmail"])
    await passwordInput.fill(InvalidInputs["password"])

    # submit form
    await basic_page.click("text=Submit")
    await basic_page.wait_for_load_state("networkidle")

    # check correct error message displayed
    assert await basic_page.locator("#loginError").inner_text() == ExpectedMessage