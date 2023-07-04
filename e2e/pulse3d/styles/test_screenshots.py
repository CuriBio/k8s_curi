import pytest

from config import TEST_URL

from fixtures import setup, video_setup, basic_page, admin_logged_in_page, user_logged_in_page

__fixtures__ = [setup, video_setup, basic_page, admin_logged_in_page, user_logged_in_page]

shared_pages = ["/uploads"]
admin_pages = []
user_pages = []


async def screen_shot_steps(page, url_to_screenshot, folder):
    await page.goto(f"https://{TEST_URL}{url_to_screenshot}")
    await page.wait_for_load_state("networkidle")

    screen_width = await page.evaluate("()=>screen.availWidth")
    screen_height = await page.evaluate("()=>screen.availHeight")
    await page.screenshot(path=f"./screenshots/{folder}/{screen_width}_{screen_height}_{url_to_screenshot}.png")


@pytest.mark.asyncio
@pytest.mark.parametrize("url_to_screenshot", shared_pages + admin_pages)
async def test_screenshot_admin_pages(admin_logged_in_page, url_to_screenshot):
    await screen_shot_steps(admin_logged_in_page, url_to_screenshot, "admin")


@pytest.mark.asyncio
@pytest.mark.parametrize("url_to_screenshot", shared_pages + user_pages)
async def test_screenshot_user_pages(user_logged_in_page, url_to_screenshot):
    await screen_shot_steps(user_logged_in_page, url_to_screenshot, "user")
