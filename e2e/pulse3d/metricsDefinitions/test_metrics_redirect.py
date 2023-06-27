import pytest

from fixtures import setup, video_setup, basic_page, user_logged_in_page

__fixtures__ = [setup, video_setup, basic_page, user_logged_in_page]

METRICS_URL = "https://pulse3d.readthedocs.io/en/latest/_images/twitch_metrics_diagram.png"


@pytest.mark.asyncio
async def test_metrics_graph_displays(user_logged_in_page):
    await user_logged_in_page.wait_for_load_state("networkidle")

    # click metrics definitions
    await user_logged_in_page.click("text=Metric Definitions")

    # assert correct page is present
    await user_logged_in_page.wait_for_load_state("networkidle")
    assert basic_page.url == METRICS_URL
