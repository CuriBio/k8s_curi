import pytest
import time

from config import VALID_CUSTOMER_ID, VALID_USER_NAME, VALID_USER_PASSWORD, TEST_URL
from fixtures import setup, video_setup, basic_page

__fixtures__ = [
    setup,
    video_setup,
    basic_page,
]


async def login(username, password, page):
    # select user login and check correct login inputs
    await page.click("text=User")
    customer_id_Input = page.get_by_placeholder("CuriBio")
    user_name_input = page.get_by_placeholder("user")
    password_input = page.get_by_placeholder("Password")

    assert await customer_id_Input.is_visible()
    assert await user_name_input.is_visible()
    assert await password_input.is_visible()

    # log in with valid user credentials
    await customer_id_Input.fill(VALID_CUSTOMER_ID)
    await user_name_input.fill(username)
    await password_input.fill(password)

    await page.click("text=Submit")
    await page.wait_for_url("**/uploads")

    # test login success
    assert page.url == f"https://{TEST_URL}/uploads"
    time.sleep(5)


@pytest.mark.asyncio
async def test_user_with_unlimited(basic_page):
    await login(VALID_USER_NAME, VALID_USER_PASSWORD, basic_page)
    assert await basic_page.get_by_text("Unlimited Access").is_visible()


@pytest.mark.asyncio
async def test_user_with_limit_reached(basic_page):
    await login(VALID_USER_NAME, VALID_USER_PASSWORD, basic_page)


@pytest.mark.asyncio
async def test_user_with_limit_not_reached(basic_page):
    await login(VALID_USER_NAME, VALID_USER_PASSWORD, basic_page)
