import pytest
import time


from fixtures import setup, video_setup, basic_page, admin_logged_in_page

__fixtures__ = [setup, video_setup, basic_page, admin_logged_in_page]


@pytest.mark.asyncio
@pytest.mark.parametrize("specificDownloadOption", ["Download Analyses", "Download Raw Data"])
async def test_Download(admin_logged_in_page, specificDownloadOption):
    await admin_logged_in_page.wait_for_load_state("networkidle")

    # select first upload from the uploads table
    upload_checboxes = admin_logged_in_page.get_by_role("checkbox")
    await upload_checboxes.nth(0).click()

    # select Dowload from Actions menu
    async with admin_logged_in_page.expect_download() as analysesDownload:
        await admin_logged_in_page.get_by_role("button", name="Actions").click()
        await admin_logged_in_page.get_by_role("option", name="Download").click()
        await admin_logged_in_page.get_by_role("option", name=specificDownloadOption).click()

        # wait for dowload to complete then check that there are no errors
        download = await analysesDownload.value
        assert await download.failure() is None


# deleting with admin seems to not be working on the test or prod cluster
@pytest.mark.asyncio
async def test_Delete(admin_logged_in_page):
    await admin_logged_in_page.wait_for_load_state("networkidle")

    # select first upload from the uploads table
    upload_checkbox = admin_logged_in_page.get_by_role("checkbox").nth(0)
    await upload_checkbox.click()

    # get name of checked box
    name_of_checked_upload = await upload_checkbox.evaluate(
        "node => node.parentNode.parentNode.parentNode.children[3].children[0].innerHTML"
    )

    # select Delete from Actions menu
    await admin_logged_in_page.get_by_role("button", name="Actions").click()
    await admin_logged_in_page.get_by_role("option", name="Delete").click()
    await admin_logged_in_page.get_by_role("button", name="Confirm").click()

    time.sleep(5)

    # check that first upload was deleted
    new_upload_column = admin_logged_in_page.get_by_role("checkbox").nth(0)
    name_of_new_upload = await new_upload_column.evaluate(
        "node => node.parentNode.parentNode.parentNode.children[3].children[0].innerHTML"
    )

    assert name_of_new_upload == name_of_checked_upload
