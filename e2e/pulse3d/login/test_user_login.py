from playwright.async_api import async_playwright
import pytest
import asyncio

pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope='session')
def loop():
    return asyncio.get_event_loop()

@pytest.fixture(scope='session')
async def myFixture(loop):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        # await page.goto("http://playwright.dev")
        yield page
        await browser.close()



# @pytest.fixture(scope='session', autouse=True)

@pytest.mark.asyncio
async def testExample(loop,page):
    await page.goto("http://playwright.dev")

# @pytest.mark.asyncio
# async def testExample2(page):
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=False)
#         page = await browser.new_page()
#         await page.goto("http://playwright.dev")
#         print(await page.title())
#         await browser.close()