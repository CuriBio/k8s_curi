import pytest

from fixtures import basic_page, setup, video_setup

from config import VALID_ADMIN_EMAIL, VALID_ADMIN_PASSWORD, TEST_URL

__fixtures__ = [basic_page, setup, video_setup]


@pytest.mark.asyncio
async def test_login_succes_admin(basic_page):
    # click to select login form for user
    await basic_page.click("text=Admin")

    # get input fields
    email_Input = basic_page.get_by_placeholder("user@curibio.com")
    password_Input = basic_page.get_by_placeholder("Password")

    # check correct input form displayed
    assert await email_Input.is_visible()
    assert await password_Input.is_visible()

    # populate form with valid credentials
    await email_Input.fill(VALID_ADMIN_EMAIL)
    await password_Input.fill(VALID_ADMIN_PASSWORD)

    # submit form
    await basic_page.click("text=Submit")
    await basic_page.wait_for_url("**/uploads")

    # check that the login was successful
    assert basic_page.url == f"https://{TEST_URL}/uploads"


invalid_admins = [
    ("*Invalid credentials. Try again.", {"adminEmail": "invalid@email.com", "password": VALID_ADMIN_EMAIL}),
    ("*Invalid credentials. Try again.", {"adminEmail": VALID_ADMIN_EMAIL, "password": "invalidPassword"}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("expected_message, invalid_inputs", invalid_admins)
async def test_invalid_inputs_admin(basic_page, expected_message, invalid_inputs):
    # click to select login form for user
    await basic_page.click("text=Admin")

    # get input fields
    email_input = basic_page.get_by_placeholder("user@curibio.com")
    password_input = basic_page.get_by_placeholder("Password")

    # check correct input form displayed
    assert await email_input.is_visible()
    assert await password_input.is_visible()

    # populate form with invalid credentials
    await email_input.fill(invalid_inputs["adminEmail"])
    await password_input.fill(invalid_inputs["password"])

    # submit form
    await basic_page.click("text=Submit")
    await basic_page.wait_for_load_state("networkidle")

    # check correct error message displayed
    assert await basic_page.locator("#loginError").inner_text() == expected_message
