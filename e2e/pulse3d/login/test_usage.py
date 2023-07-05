import pytest
import time

from config import (
    VALID_ADMIN_EMAIL,
    VALID_ADMIN_PASSWORD,
    TEST_URL,
    LIMIT_NOT_REACHED_EMAIL,
    LIMIT_NOT_REACHED_PASSWORD,
    LIMIT_REACHED_EMAIL,
    LIMIT_REACHED_PASSWORD,
)
from fixtures import setup, video_setup, basic_page

__fixtures__ = [
    setup,
    video_setup,
    basic_page,
]


async def login_with_admin(email, password, page):
    # select user login and check correct login inputs
    await page.click("text=Admin")
    customer_email_input = page.get_by_placeholder("user@curibio.com")
    password_input = page.get_by_placeholder("Password")

    assert await customer_email_input.is_visible()
    assert await password_input.is_visible()

    await customer_email_input.fill(email)
    await password_input.fill(password)

    await page.click("text=Submit")
    await page.wait_for_url("**/uploads")

    # test login success
    assert page.url == f"https://{TEST_URL}/uploads"
    time.sleep(5)


@pytest.mark.asyncio
async def test_admin_with_unlimited(basic_page):
    await login_with_admin(VALID_ADMIN_EMAIL, VALID_ADMIN_PASSWORD, basic_page)
    assert await basic_page.get_by_text("Unlimited Access").is_visible()


@pytest.mark.asyncio
async def test_admin_with_limit_not_reached(basic_page):
    await login_with_admin(LIMIT_NOT_REACHED_EMAIL, LIMIT_NOT_REACHED_PASSWORD, basic_page)
    assert await basic_page.get_by_text("Usage")._is_visible()
    assert await basic_page.get_by_text("0%")._is_visible()
    assert await basic_page.get_by_text("0/100 Analysis used")._is_visible()
    assert await basic_page.get_by_text("UPGRADE")._is_visible()


@pytest.mark.asyncio
async def test_admin_with_limit_reached(basic_page):
    await login_with_admin(LIMIT_REACHED_EMAIL, LIMIT_REACHED_PASSWORD, basic_page)
    assert await basic_page.get_by_text("Warning!")._is_visible()
    await basic_page.click("text=Close")
    assert await basic_page.get_by_text("Plan Has Expired")._is_visible()
    assert await basic_page.get_by_text("UPGRADE")._is_visible()
