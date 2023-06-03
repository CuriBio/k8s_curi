import os
import pytest
from playwright.sync_api import sync_playwright

VALID_CUSTOMER_ID = os.getenv("VALID_USER_ID")
VALID_USER_NAME = os.getenv("VALID_USER_NAME")
VALID_USER_PASSWORD = os.getenv("VALID_USER_PASSWORD")
TEST_URL = os.getenv("TEST_URL")


@pytest.mark.parametrize("browser_type", ["chromium", "firefox", "webkit"])
def test_login_succes_for_user(browser_type):

    with sync_playwright() as p:
        browser = getattr(p, browser_type).launch_persistent_context("profile", headless=False)
        page = browser.new_page()

        page.goto(f"{TEST_URL}/login")

        # click to select login form for user
        page.click('text=User')

        # get input fields
        customerId = page.get_by_placeholder("CuriBio")
        userName = page.get_by_placeholder("user")
        password = page.get_by_placeholder("Password")

        # check correct input form displayed
        assert customerId.is_visible()
        assert userName.is_visible()
        assert password.is_visible()

        # populate form with valid credentials
        customerId.fill(VALID_CUSTOMER_ID)
        userName.fill(VALID_USER_NAME)
        password.fill(VALID_USER_PASSWORD)

        # submit form
        page.click('text=Submit')
        page.wait_for_url("**/uploads")

        # check that the login was successful
        assert page.url == f"http://{TEST_URL}/uploads"
        browser.close()
