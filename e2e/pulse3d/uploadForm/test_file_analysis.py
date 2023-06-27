import pytest

from fixtures import setup, video_setup, basic_page, user_logged_in_page
from config import TEST_URL

__fixtures__ = [setup, video_setup, basic_page, user_logged_in_page]


supported_file_formats = [
    "ZIPPED_H5_FILES.zip"
]  # ,"one_zipped_optical_file","one_optical_file","zipped_h5_files","one_zipped_h5_file","one_h5_file"]


@pytest.mark.asyncio
@pytest.mark.parametrize("test_file_name", supported_file_formats)
async def test_new_uploads_runs_correctly(user_logged_in_page, test_file_name):
    # navigate to new upload page
    await user_logged_in_page.click("text=Run Analysis")
    await user_logged_in_page.click("text=Analyze New Files")
    await user_logged_in_page.wait_for_load_state("networkidle")

    # make sure correct page is loaded
    new_file_dropdown = await user_logged_in_page.query_selector("div:has-text('CLICK HERE or DROP')")
    assert await new_file_dropdown.is_visible()

    # upload file
    async with user_logged_in_page.expect_file_chooser() as fc_info:
        await new_file_dropdown.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(f"testFiles/{test_file_name}")

    # submit analasys
    await user_logged_in_page.click("text=Submit")
    await user_logged_in_page.wait_for_selector("span:has-text('Upload Successful!')", state="visible")

    # check analasys was succesfully added to upload table
    # navigate to uploads table
    await user_logged_in_page.goto(f"https://{TEST_URL}/uploads")
    await user_logged_in_page.wait_for_load_state("networkidle")

    # get first upload, check names match
    upload_row_checkbox = user_logged_in_page.get_by_role("checkbox").nth(0)
    upload_row_name = await upload_row_checkbox.evaluate(
        "node => node.parentNode.parentNode.parentNode.children[2].children[0].innerHTML"
    )
    assert upload_row_name == test_file_name.rpartition(".")[0]

    # check that upload is not in error state
    await upload_row_checkbox.evaluate(
        "node => node.parentNode.parentNode.parentNode.children[0].children[0].click()"
    )
    # 1 and last child
    assert (
        await user_logged_in_page.get_by_text("Pending").is_visible()
        or await user_logged_in_page.get_by_text("Running").is_visible()
    )


@pytest.mark.asyncio
async def test_reanalysis_runs_correctly(user_logged_in_page):
    # navigate to reanalysis page
    await user_logged_in_page.click("text=Run Analysis")
    await user_logged_in_page.click("text=Re-analyze Existing Upload")
    await user_logged_in_page.wait_for_load_state("networkidle")

    # make sure correct page is loaded
    reanalasys_input = await user_logged_in_page.query_selector("label:has-text('Select Recording')")
    assert await reanalasys_input.is_visible()

    # select file to re-analyze from dropdown
    await user_logged_in_page.click("css=[title='Open']")
    dropdown = await user_logged_in_page.query_selector("ul.MuiAutocomplete-listbox")
    file_to_reanalyze_name = await dropdown.evaluate("node=>node.children[0].innerHTML")
    await dropdown.evaluate("node=>node.children[0].click()")
    await user_logged_in_page.get_by_text("Submit").click()

    # This message shows up for a second then disappears, So this part of the test is commented out until the bug is fixed
    # await user_logged_in_page.wait_for_selector("span:has-text('Upload Successful!')", state='visible')

    # after upload is succesfull check that first upload in uploads list is correct
    await user_logged_in_page.goto(f"https://{TEST_URL}/uploads")
    await user_logged_in_page.wait_for_load_state("networkidle")
    upload_checkbox = user_logged_in_page.get_by_role("checkbox").nth(0)
    name_of_new_upload = await upload_checkbox.evaluate(
        "node => node.parentNode.parentNode.parentNode.children[2].children[0].innerHTML"
    )
    assert name_of_new_upload == file_to_reanalyze_name.rpartition(".")[0]
