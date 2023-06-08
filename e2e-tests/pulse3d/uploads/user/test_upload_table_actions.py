import time
import pytest

from config import TEST_URL

from fixtures import loginUser


def test_ReAnalyze(page):
    page.goto(f"{TEST_URL}/uploads")
    page.wait_for_load_state("networkidle")

    # select an upload from the uploads table
    upload_checboxes = page.get_by_role("checkbox")
    upload_checboxes.nth(0).click()

    # select Re-Analyze from Actions menu
    page.get_by_role("button", name="Actions").click()
    page.get_by_role("option", name="Re-Analyze").click()
    page.wait_for_url("**/upload-form?id=Re-analyze+Existing+Upload")

    # submit analasys
    page.get_by_role("button", name="Submit").click()

    # check upload was succes
    assert page.get_by_text("Error Occurred").is_visible() == False


@pytest.mark.parametrize("spesificDownloadOption", ["Download Analyses", "Download Raw Data"])
def test_Download(page, spesificDownloadOption):
    page.goto(f"{TEST_URL}/uploads")
    page.wait_for_load_state("networkidle")

    # select first upload from the uploads table
    upload_checboxes = page.get_by_role("checkbox")
    upload_checboxes.nth(0).click()

    # select Dowload from Actions menu
    with page.expect_download() as analysesDownload:
        page.get_by_role("button", name="Actions").click()
        page.get_by_role("option", name="Download").click()
        page.get_by_role("option", name=spesificDownloadOption).click()

        # wait for dowload to complete then check that there are no errors
        download = analysesDownload.value
        assert download.failure() == None


def test_Delete(page):
    page.goto(f"{TEST_URL}/uploads")
    page.wait_for_load_state("networkidle")

    # select first upload from the uploads table
    upload_checkbox = page.get_by_role("checkbox").nth(0)
    upload_checkbox.click()

    # get name of checked box
    nameOfCheckedUpload = upload_checkbox.evaluate(
        "node => node.parentNode.parentNode.parentNode.children[2].children[0].innerHTML"
    )

    # select Delete from Actions menu
    page.get_by_role("button", name="Actions").click()
    page.get_by_role("option", name="Delete").click()
    page.get_by_role("button", name="Confirm").click()

    # wait for response to complete
    # TODO change this to wait for a request to finish or somthign better
    time.sleep(5.1)
    page.wait_for_load_state("networkidle")

    # check that first upload was deleted
    newUploadColumn = page.get_by_role("checkbox").nth(0)
    nameOfNewUpload = newUploadColumn.evaluate(
        "node => node.parentNode.parentNode.parentNode.children[2].children[0].innerHTML"
    )

    assert nameOfNewUpload != nameOfCheckedUpload


def test_Open_IA(page):
    page.goto(f"{TEST_URL}/uploads")
    page.wait_for_load_state("networkidle")

    # select first job in first upload
    checkboxInFistRow = page.get_by_role("checkbox").nth(0)
    checkboxInFistRow.evaluate(
        "node => node.parentNode.parentNode.parentNode.children[0].children[0].click()"
    )
    page.get_by_role("checkbox").nth(1).click()

    # select Interactive Analysis from Actions menu
    page.get_by_role("button", name="Actions").click()
    page.get_by_role("option", name="Interactive Analysis").click()

    # check IA was opened
    assert page.get_by_text("Interactive Waveform Analysis").is_visible() == True
