import pytest
from config import TEST_URL,VALID_CUSTOMER_ID,VALID_USER_NAME,VALID_USER_PASSWORD

from fixtures import basic_page,setup,video_setup

@pytest.mark.asyncio
async def test_login_success_user(basic_page):
    # select user login and check correct login inputs
    await basic_page.click("text=User")
    customerIdInput = basic_page.get_by_placeholder("CuriBio")
    userNameInput = basic_page.get_by_placeholder("user")
    passwordInput = basic_page.get_by_placeholder("Password")

    assert await customerIdInput.is_visible()
    assert await userNameInput.is_visible()
    assert await passwordInput.is_visible()

    # log in with valid user credentials
    await customerIdInput.fill(VALID_CUSTOMER_ID)
    await userNameInput.fill(VALID_USER_NAME)
    await passwordInput.fill(VALID_USER_PASSWORD)

    await basic_page.click("text=Submit")
    await basic_page.wait_for_url("**/uploads")

    # test login success
    assert basic_page.url == f"https://{TEST_URL}/uploads"


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
@pytest.mark.asyncio
@pytest.mark.parametrize("ExpectedMessage, InvalidInputs", invalidUsers)
async def test_invalid_inputs_user(basic_page, ExpectedMessage, InvalidInputs):
    # click to select login form for user
    await basic_page.click("text=User")

    # get input fields
    customerIdInput =  basic_page.get_by_placeholder("CuriBio")
    userNameInput =  basic_page.get_by_placeholder("user")
    passwordInput =  basic_page.get_by_placeholder("Password")

    # check correct input form displayed
    assert await customerIdInput.is_visible()
    assert await userNameInput.is_visible()
    assert await passwordInput.is_visible()

    # populate form with invalid credentials
    await customerIdInput.fill(InvalidInputs["customerId"])
    await userNameInput.fill(InvalidInputs["username"])
    await passwordInput.fill(InvalidInputs["password"])

    # submit form
    await basic_page.click("text=Submit")
    await basic_page.wait_for_load_state("networkidle")

    # check correct error message displayed
    assert await basic_page.locator("#loginError").inner_text() == ExpectedMessage