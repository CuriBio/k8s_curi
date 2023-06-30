import pytest

from fixtures import setup, video_setup, basic_page, user_logged_in_page  # noqa: F401


@pytest.mark.asyncio
async def test_ReAnalyze(user_logged_in_page):  # noqa: F811
    # select an upload from the uploads table
    await user_logged_in_page.wait_for_load_state("networkidle")
    upload_checboxes = user_logged_in_page.get_by_role("checkbox")
    await upload_checboxes.nth(0).click()

    # select Re-Analyze from Actions menu
    await user_logged_in_page.get_by_role("button", name="Actions").click()
    await user_logged_in_page.get_by_role("option", name="Re-Analyze").click()
    await user_logged_in_page.wait_for_url("**/upload-form?id=Re-analyze+Existing+Upload")

    # submit analasys
    await user_logged_in_page.get_by_role("button", name="Submit").click()

    # check upload was succes
    assert await user_logged_in_page.get_by_text("Error Occurred").is_visible() is False


@pytest.mark.asyncio
@pytest.mark.parametrize("spesificDownloadOption", ["Download Analyses", "Download Raw Data"])
async def test_Download(user_logged_in_page, spesificDownloadOption):  # noqa: F811
    await user_logged_in_page.wait_for_load_state("networkidle")

    # select first upload from the uploads table
    upload_checboxes = user_logged_in_page.get_by_role("checkbox")
    await upload_checboxes.nth(0).click()

    # select Dowload from Actions menu
    async with user_logged_in_page.expect_download() as analysesDownload:
        await user_logged_in_page.get_by_role("button", name="Actions").click()
        await user_logged_in_page.get_by_role("option", name="Download").click()
        await user_logged_in_page.get_by_role("option", name=spesificDownloadOption).click()

        # wait for dowload to complete then check that there are no errors
        download = await analysesDownload.value
        assert await download.failure() is None


@pytest.mark.asyncio
async def test_Delete(user_logged_in_page):  # noqa: F811
    await user_logged_in_page.wait_for_load_state("networkidle")

    # select first upload from the uploads table
    upload_checkbox = user_logged_in_page.get_by_role("checkbox").nth(0)
    await upload_checkbox.click()

    # get name of checked box
    name_of_checked_upload = await upload_checkbox.evaluate(
        "node => node.parentNode.parentNode.parentNode.children[2].children[0].innerHTML"
    )

    # select Delete from Actions menu
    await user_logged_in_page.get_by_role("button", name="Actions").click()
    await user_logged_in_page.get_by_role("option", name="Delete").click()
    await user_logged_in_page.get_by_role("button", name="Confirm").click()

    # element_id = await upload_checkbox.evaluate("element => element.id")

    # wait for response to complete
    # await user_logged_in_page.wait_for_selector(f'#{element_id}', state='hidden')

    # check that first upload was deleted
    new_upload_column = user_logged_in_page.get_by_role("checkbox").nth(0)
    name_of_new_upload = await new_upload_column.evaluate(
        "node => node.parentNode.parentNode.parentNode.children[2].children[0].innerHTML"
    )

    assert name_of_new_upload != name_of_checked_upload


@pytest.mark.asyncio
async def test_Open_IA(user_logged_in_page):  # noqa: F811
    await user_logged_in_page.wait_for_load_state("networkidle")

    # select first job in first upload
    checkbox_in_fist_row = user_logged_in_page.get_by_role("checkbox").nth(0)
    await checkbox_in_fist_row.evaluate(
        "node => node.parentNode.parentNode.parentNode.children[0].children[0].click()"
    )
    await user_logged_in_page.get_by_role("checkbox").nth(1).click()

    # select Interactive Analysis from Actions menu
    await user_logged_in_page.get_by_role("button", name="Actions").click()
    await user_logged_in_page.get_by_role("option", name="Interactive Analysis").click()

    # check IA was opened
    assert await user_logged_in_page.get_by_text("Interactive Waveform Analysis").is_visible() is True