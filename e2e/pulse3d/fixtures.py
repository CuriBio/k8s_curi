import pytest_asyncio,pytest
import shutil
from playwright.async_api import async_playwright
from config import TEST_URL,VALID_CUSTOMER_ID,VALID_USER_NAME,VALID_USER_PASSWORD,HEADLESS

# remove older videos if present
@pytest.fixture(scope="session", autouse=True)
def video_setup():
    shutil.rmtree("./videos/")


@pytest_asyncio.fixture(scope="function", name="setup")
async def setup(request):
     async with async_playwright() as p:
        test_name = request.node.name.split("[")[0]

        browser = await p.chromium.launch(headless=HEADLESS,slow_mo=1000)
        context = await browser.new_context(record_video_dir=f"videos/{test_name}")
        page = await context.new_page()

        yield page

        await page.close()
        await context.close()
        await browser.close()

        # save only videos of failed tests
        if not request.node.rep_call.failed:
            shutil.rmtree(f"./videos/{test_name}")


@pytest_asyncio.fixture(scope="function", name="basic_page")
async def basic_page(setup):
    await setup.goto(f"https://{TEST_URL}/login")
    await setup.wait_for_load_state("networkidle")
    await setup.reload()
    assert await setup.title() == 'Pulse Analysis'

    yield setup
        
        
@pytest_asyncio.fixture(scope="function", name="user_logged_in_page")
async def user_logged_in_page(basic_page):
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

    yield basic_page