import os
from playwright.sync_api import sync_playwright

VALID_CUSTOMER_ID = os.getenv("VALID_USER_ID")
VALID_USER_NAME = os.getenv("VALID_USER_NAME")
VALID_USER_PASSWORD = os.getenv("VALID_USER_PASSWORD")


def test_login_succes_for_user(browser_type):

    browser = browser_type.launch_persistent_context("profile", headless=False)
    page = browser.new_page()

    page.goto("localhost:3000/login")

    # click to select login form for user
    page.get_by_role("button", name="User").click()

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
    page.get_by_role("button", name="Submit").click()
    page.wait_for_url("**/uploads")

    # check that the login was succesfull
    assert page.url == "http://localhost:3000/uploads"
    browser.close()


with sync_playwright() as p:
    for browser_type in [p.chromium, p.firefox, p.webkit]:
        test_login_succes_for_user(browser_type)