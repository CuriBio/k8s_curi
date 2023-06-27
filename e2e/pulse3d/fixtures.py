from playwright.async_api import async_playwright
import pytest_asyncio
import pytest
import shutil

from config import (
    TEST_URL,
    VALID_CUSTOMER_ID,
    VALID_USER_NAME,
    VALID_USER_PASSWORD,
    VALID_ADMIN_EMAIL,
    VALID_ADMIN_PASSWORD,
    HEADLESS,
    SLOWMO,
)


# remove older videos if present
@pytest.fixture(scope="session", autouse=True)
def video_setup():
    shutil.rmtree("./videos/")


# set up basic browser and context
@pytest_asyncio.fixture(scope="function", name="setup")
async def setup(request):
    async with async_playwright() as p:
        test_name = request.node.name.split("[")[0]

        browser = await p.chromium.launch(headless=HEADLESS, slow_mo=1000 if SLOWMO else None)
        context = await browser.new_context(record_video_dir=f"videos/{test_name}")
        page = await context.new_page()

        yield page

        await page.close()
        await context.close()
        await browser.close()

        # save only videos of failed tests
        if not request.node.rep_call.failed:
            shutil.rmtree(f"./videos/{test_name}")


# navigate to login page
@pytest_asyncio.fixture(scope="function", name="basic_page")
async def basic_page(setup):
    await setup.goto(f"https://{TEST_URL}/login")
    await setup.wait_for_load_state("networkidle")
    await setup.reload()
    assert await setup.title() == "Pulse Analysis"

    yield setup


# login before user test
@pytest_asyncio.fixture(scope="function", name="user_logged_in_page")
async def user_logged_in_page(basic_page):
    # click to select login form for user
    await basic_page.click("text=User")

    # get input fields
    customer_id_input = basic_page.get_by_placeholder("CuriBio")
    user_name_input = basic_page.get_by_placeholder("user")
    password_input = basic_page.get_by_placeholder("Password")

    assert await customer_id_input.is_visible()
    assert await user_name_input.is_visible()
    assert await password_input.is_visible()

    # log in with valid user credentials
    await customer_id_input.fill(VALID_CUSTOMER_ID)
    await user_name_input.fill(VALID_USER_NAME)
    await password_input.fill(VALID_USER_PASSWORD)

    await basic_page.click("text=Submit")
    await basic_page.wait_for_url("**/uploads")

    # test login success
    assert basic_page.url == f"https://{TEST_URL}/uploads"

    yield basic_page


# login before admin tests
@pytest_asyncio.fixture(scope="function", name="admin_logged_in_page")
async def admin_logged_in_page(basic_page):
    # click to select login form for admin
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

    yield basic_page
