import pytest
from fixtures import setup,video_setup, basic_page,user_logged_in_page

@pytest.mark.asyncio
async def test_ReAnalyze(user_logged_in_page):
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
    assert await user_logged_in_page.get_by_text("Error Occurred").is_visible() == False


@pytest.mark.asyncio
@pytest.mark.parametrize("spesificDownloadOption", ["Download Analyses", "Download Raw Data"])
async def test_Download(user_logged_in_page, spesificDownloadOption):
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
        assert  await download.failure() == None


@pytest.mark.asyncio
async def test_Delete(user_logged_in_page):
    await user_logged_in_page.wait_for_load_state("networkidle")

    # select first upload from the uploads table
    upload_checkbox = user_logged_in_page.get_by_role("checkbox").nth(0)
    await upload_checkbox.click()

    # get name of checked box
    nameOfCheckedUpload = await upload_checkbox.evaluate(
        "node => node.parentNode.parentNode.parentNode.children[2].children[0].innerHTML"
    )

    # select Delete from Actions menu
    await user_logged_in_page.get_by_role("button", name="Actions").click()
    await user_logged_in_page.get_by_role("option", name="Delete").click()
    await user_logged_in_page.get_by_role("button", name="Confirm").click()

    element_id = await upload_checkbox.evaluate('element => element.id')

    # wait for response to complete
    # await user_logged_in_page.wait_for_selector(f'#{element_id}', state='hidden')

    # check that first upload was deleted
    newUploadColumn = user_logged_in_page.get_by_role("checkbox").nth(0)
    nameOfNewUpload = await newUploadColumn.evaluate(
        "node => node.parentNode.parentNode.parentNode.children[2].children[0].innerHTML"
    )

    assert nameOfNewUpload != nameOfCheckedUpload


@pytest.mark.asyncio
async def test_Open_IA(user_logged_in_page):
    await user_logged_in_page.wait_for_load_state("networkidle")

    # select first job in first upload
    checkboxInFistRow = user_logged_in_page.get_by_role("checkbox").nth(0)
    await checkboxInFistRow.evaluate(
        "node => node.parentNode.parentNode.parentNode.children[0].children[0].click()"
    )
    await user_logged_in_page.get_by_role("checkbox").nth(1).click()

    # select Interactive Analysis from Actions menu
    await user_logged_in_page.get_by_role("button", name="Actions").click()
    await user_logged_in_page.get_by_role("option", name="Interactive Analysis").click()

    # check IA was opened
    assert await user_logged_in_page.get_by_text("Interactive Waveform Analysis").is_visible() == True