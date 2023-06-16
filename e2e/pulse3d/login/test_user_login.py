import pytest

from fixtures import basic_page, setup, video_setup

from config import TEST_URL, VALID_CUSTOMER_ID, VALID_USER_NAME, VALID_USER_PASSWORD


@pytest.mark.asyncio
async def test_login_success_user(basic_page):
    # select user login and check correct login inputs
    await basic_page.click("text=User")
    customer_id_Input = basic_page.get_by_placeholder("CuriBio")
    user_name_input = basic_page.get_by_placeholder("user")
    password_input = basic_page.get_by_placeholder("Password")

    assert await customer_id_Input.is_visible()
    assert await user_name_input.is_visible()
    assert await password_input.is_visible()

    # log in with valid user credentials
    await customer_id_Input.fill(VALID_CUSTOMER_ID)
    await user_name_input.fill(VALID_USER_NAME)
    await password_input.fill(VALID_USER_PASSWORD)

    await basic_page.click("text=Submit")
    await basic_page.wait_for_url("**/uploads")

    # test login success
    assert basic_page.url == f"https://{TEST_URL}/uploads"


invalid_users = [
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


@pytest.mark.asyncio
@pytest.mark.parametrize("Expected_message, Invalid_inputs", invalid_users)
async def test_invalid_inputs_user(basic_page, Expected_message, Invalid_inputs):
    # click to select login form for user
    await basic_page.click("text=User")

    # get input fields
    customer_id_Input = basic_page.get_by_placeholder("CuriBio")
    user_name_input = basic_page.get_by_placeholder("user")
    password_input = basic_page.get_by_placeholder("Password")

    # check correct input form displayed
    assert await customer_id_Input.is_visible()
    assert await user_name_input.is_visible()
    assert await password_input.is_visible()

    # populate form with invalid credentials
    await customer_id_Input.fill(Invalid_inputs["customerId"])
    await user_name_input.fill(Invalid_inputs["username"])
    await password_input.fill(Invalid_inputs["password"])

    # submit form
    await basic_page.click("text=Submit")
    await basic_page.wait_for_load_state("networkidle")

    # check correct error message displayed
    assert await basic_page.locator("#loginError").inner_text() == Expected_message
