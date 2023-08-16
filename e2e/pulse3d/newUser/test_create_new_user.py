import pytest
import random
import string
import time

from config import DASHBOARD_URL

from fixtures import (
    setup,
    video_setup,
    basic_page,
    admin_logged_in_page,
)

__fixtures__ = [
    setup,
    video_setup,
    basic_page,
    admin_logged_in_page,
]


# set up test for /new-user page
async def goto_user_creation(page):
    await page.click("text=Add New User")
    await page.wait_for_url("**/new-user")

    # check correct page is loaded
    assert page.url == f"https://{DASHBOARD_URL}/new-user"


@pytest.mark.asyncio
async def test_valid_new_user_credentials(admin_logged_in_page):
    await goto_user_creation(admin_logged_in_page)
    new_user_name = "".join(random.choices(string.ascii_letters + string.digits, k=5))
    new_user_email = f"{new_user_name}@testcuribio.com"
    # get input fields

    email_input = admin_logged_in_page.get_by_placeholder("user@curibio.com")
    username_input = admin_logged_in_page.get_by_placeholder("User").nth(1)

    # fill and reset
    await email_input.fill(new_user_email)
    await username_input.fill(new_user_name)
    await admin_logged_in_page.click("text=Reset")

    # fill again and submit
    await email_input.fill(new_user_email)
    await username_input.fill(new_user_name)
    await admin_logged_in_page.click("text=Add User")

    # wait for api calls to reflect
    time.sleep(5)

    assert await admin_logged_in_page.get_by_text("Success").nth(0).is_visible()

    # todo visit users table


invalid_usernames = [
    "1username",
    "!username",
    "user name",
    "user$name",
    "user&name",
    "user%name",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_username", invalid_usernames)
async def test_invalid_new_user_credentials(admin_logged_in_page, invalid_username):
    await goto_user_creation(admin_logged_in_page)
    email_input = admin_logged_in_page.get_by_placeholder("user@curibio.com")
    username_input = admin_logged_in_page.get_by_placeholder("User").nth(1)

    new_user_email = f"{invalid_username}@testcuribio.com"

    await email_input.fill(new_user_email)
    await username_input.fill(invalid_username)

    await admin_logged_in_page.click("text=Add User")
    time.sleep(1)

    assert await admin_logged_in_page.get_by_text("* field required").is_visible()
