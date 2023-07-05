from playwright.async_api import async_playwright
import pytest_asyncio
import pytest
import os
import shutil
import glob

from config import (
    TEST_URL,
    VALID_CUSTOMER_ID,
    VALID_USER_NAME,
    VALID_USER_PASSWORD,
    VALID_ADMIN_EMAIL,
    VALID_ADMIN_PASSWORD,
)


def remove_empty_folders(path):
    for dirpath, dirnames, files in os.walk(path, topdown=False):
        if not dirnames and not files:
            os.rmdir(dirpath)


# remove older videos if present
@pytest.fixture(scope="session", autouse=True)
def video_setup():
    videos_dir = "./utils/videos/"
    if os.path.exists(videos_dir):
        shutil.rmtree(videos_dir)
    yield
    remove_empty_folders(videos_dir)


@pytest_asyncio.fixture(scope="function", name="setup")
async def setup(request, headless, slow_mo):
    test_folder = request.node.name.split("[")[0]
    video_dir = f"./utils/videos/{test_folder}"

    test_name = request.node.name
    invalid_chars = ["\\", "<", ">", ":", '"', "/", "|", "?", "*", "[", "]"]
    for char in invalid_chars:
        test_name = test_name.replace(char, "_")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, slow_mo=slow_mo)
        context = await browser.new_context(
            record_video_dir=video_dir,
        )
        page = await context.new_page()

        yield page
        await page.close()
        await context.close()
        await browser.close()

        # save videos if failed test
        list_of_files = glob.glob(os.path.join(video_dir, "*.webm"))
        latest_file = max(list_of_files, key=os.path.getctime)

        if request.node.rep_call.failed:
            os.rename(latest_file, os.path.join(video_dir, f"{test_name}.webm"))
        else:
            os.remove(latest_file)


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
