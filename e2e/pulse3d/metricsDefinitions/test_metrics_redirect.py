import pytest
import asyncio

from fixtures import setup, video_setup, basic_page, user_logged_in_page

__fixtures__ = [setup, video_setup, basic_page, user_logged_in_page]

METRICS_URL = "https://pulse3d.readthedocs.io/en/latest/_images/twitch_metrics_diagram.png"


@pytest.mark.asyncio
async def test_metrics_graph_displays(user_logged_in_page):
    await user_logged_in_page.wait_for_load_state("networkidle")

    new_page_promise = asyncio.Future()
    user_logged_in_page.once("popup", lambda popup: new_page_promise.set_result(popup))

    # click metrics definitions
    await user_logged_in_page.click("text=Metric Definitions")

    new_page = await new_page_promise

    # check new page opened
    assert new_page

    # check correct page opened
    assert new_page.url == METRICS_URL
