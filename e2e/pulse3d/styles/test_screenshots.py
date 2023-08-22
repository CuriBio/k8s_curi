import pytest

from config import DASHBOARD_URL

from fixtures import setup, video_setup, basic_page, admin_logged_in_page, user_logged_in_page

__fixtures__ = [setup, video_setup, basic_page, admin_logged_in_page, user_logged_in_page]

shared_pages = ["/uploads", "/account-settings"]
admin_pages = ["/new-user", "/users-info"]
user_pages = [
    "/upload-form?id=Analyze+New+Files",
    "/upload-form?id=Re-analyze+Existing+Upload",
]
view_ports = [(800, 600), (1024, 768), (1280, 720), (1920, 1080)]


async def screen_shot_steps(page, url_to_screenshot, folder):
    await page.wait_for_load_state("networkidle")
    for view in view_ports:
        await page.set_viewport_size({"width": view[0], "height": view[1]})
        screen_width = await page.evaluate("()=>screen.availWidth")
        screen_height = await page.evaluate("()=>screen.availHeight")
        invalid_chars = ["\\", "<", ">", ":", '"', "/", "|", "?", "*", "[", "]"]
        for char in invalid_chars:
            url_to_screenshot = url_to_screenshot.replace(char, "_")

        await page.screenshot(
            path=f"./utils/screenshots/{folder.lower()}/{screen_width}_{screen_height}/_{url_to_screenshot}.png"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("url_to_screenshot", shared_pages + admin_pages)
async def test_screenshot_admin_pages(admin_logged_in_page, url_to_screenshot):
    await admin_logged_in_page.goto(f"https://{DASHBOARD_URL}{url_to_screenshot}")
    await admin_logged_in_page.wait_for_url(f"https://{DASHBOARD_URL}{url_to_screenshot}")
    await screen_shot_steps(admin_logged_in_page, url_to_screenshot, "admin")


@pytest.mark.asyncio
@pytest.mark.parametrize("url_to_screenshot", shared_pages + user_pages)
async def test_screenshot_user_pages(user_logged_in_page, url_to_screenshot):
    await user_logged_in_page.goto(f"https://{DASHBOARD_URL}{url_to_screenshot}")
    await user_logged_in_page.wait_for_url(f"https://{DASHBOARD_URL}{url_to_screenshot}")
    await screen_shot_steps(user_logged_in_page, url_to_screenshot, "user")


@pytest.mark.asyncio
@pytest.mark.parametrize("account_type", ["Admin", "User"])
async def test_screenshot_admin_login_page(basic_page, account_type):
    await basic_page.click(f"text={account_type}")
    await screen_shot_steps(basic_page, "", account_type)
