import pytest
from config import DASHBOARD_URL
from fixtures import setup, video_setup, basic_page, user_logged_in_page

__fictures__ = [setup, video_setup, basic_page, user_logged_in_page]


input_options = [
    ("maxY", ["100"], ["g"]),
    ("twitchWidths", ["100"], ["g"]),
    ("wellsWithFlippedWaveforms", ["A1,B3"], ["g"]),
    ("baseToPeak", ["100"], ["g"]),
    ("peakToBase", ["100"], ["g"]),
    ("startTime", ["100"], ["g"]),
    ("endTime", ["100"], ["g"]),
    ("noiseProminenceFactor", ["100"], ["g"]),
    ("relativeProminenceFactor", ["100"], ["g"]),
    ("minPeakHeight", ["100"], ["g"]),
    ("maxPeakFreq", ["100"], ["g"]),
    ("valleySearchDuration", ["100"], ["g"]),
    ("upslopeDuration", ["100"], ["g"]),
    ("upslopeNoiseAllowance", ["100"], ["g"]),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("input_id, valid_inputs, invalid_inputs", input_options)
async def test_custom_number_input_options(
    user_logged_in_page,
    input_id,
    valid_inputs,
    invalid_inputs,
):
    await user_logged_in_page.goto(f"https://{DASHBOARD_URL}/upload-form")
    await user_logged_in_page.wait_for_load_state("networkidle")

    # click param switch
    param_switch_text = await user_logged_in_page.query_selector("input.PrivateSwitchBase-input")
    await param_switch_text.evaluate("node=>node.click()")

    # get input box
    input_box = await user_logged_in_page.query_selector(f"input#{input_id}")

    # test all valid inputs
    for valid_input in valid_inputs:
        await input_box.fill(valid_input)
        error_msg_component = await user_logged_in_page.query_selector(f"span#{input_id}Error")
        error_msg = await error_msg_component.evaluate("node=>node.innerHTML")
        assert error_msg == ""
        await input_box.fill("")

    # test invalid inputs
    for invalid_input in invalid_inputs:
        await input_box.fill(invalid_input)
        error_msg_component = await user_logged_in_page.query_selector(f"span#{input_id}Error")
        error_msg = await error_msg_component.evaluate("node=>node.innerHTML")
        assert error_msg != ""
        await input_box.fill("")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "inputs",
    [
        ("1", "2", True),
        ("1", "", True),
        ("", "2", True),
        ("2", "1", False),
        ("-1", "-2", False),
    ],
)
async def test_advanced_analysis_valid_width_inputs(user_logged_in_page, inputs):
    await user_logged_in_page.goto(f"https://{DASHBOARD_URL}/upload-form?id=Re-analyze+Existing+Upload")
    await user_logged_in_page.wait_for_load_state("networkidle")
    # click param switch
    param_switch_text = await user_logged_in_page.query_selector("input.PrivateSwitchBase-input")
    await param_switch_text.evaluate("node=>node.click()")
    # get input boxes
    input_box_min = await user_logged_in_page.query_selector("input#minPeakWidth")
    input_box_max = await user_logged_in_page.query_selector("input#maxPeakWidth")

    # test input combo
    await input_box_min.fill(inputs[0])
    await input_box_max.fill(inputs[1])
    min_error_msg_component = await user_logged_in_page.query_selector("span#minPeakWidthError")
    max_error_msg_component = await user_logged_in_page.query_selector("span#maxPeakWidthError")
    error_msg = await min_error_msg_component.evaluate("node=>node.innerHTML")
    error_msg += await max_error_msg_component.evaluate("node=>node.innerHTML")
    if inputs[2]:
        assert error_msg == ""
    else:
        assert error_msg != ""


async def setUpWellGroupingsTest(page):
    await page.goto(f"https://{DASHBOARD_URL}/upload-form?id=Re-analyze+Existing+Upload")
    await page.wait_for_load_state("networkidle")
    # click param switch
    param_switch_text = await page.query_selector("input.PrivateSwitchBase-input")
    await param_switch_text.evaluate("node=>node.click()")
    # get inputs
    add_grouping = await page.query_selector("svg[data-testid='AddCircleOutlineIcon']")
    return add_grouping


@pytest.mark.asyncio
async def test_well_groupings_option_invalid_inputs(user_logged_in_page):
    inputs = [
        ("", "randomString"),
        ("", "a3,b3,c4"),
        ("", ""),
    ]
    add_grouping = await setUpWellGroupingsTest(user_logged_in_page)
    # test invalid inputs
    for index, input in enumerate(inputs):
        await add_grouping.click()
        # get inputs
        await user_logged_in_page.get_by_placeholder("Label Name").nth(index).fill(input[0])
        await user_logged_in_page.get_by_placeholder("A1, B2, C3").nth(index).fill(input[1])
        # get error msg
        label_error_components = await user_logged_in_page.query_selector_all("span#labelNameError")
        wells_error_components = await user_logged_in_page.query_selector_all("span#wellsError")
        current_label_error_components = label_error_components[index]
        current_wells_error_components = wells_error_components[index]
        label_error_msg = await current_label_error_components.evaluate("node=>node.innerHTML")
        well_error_msg = await current_wells_error_components.evaluate("node=>node.innerHTML")
        assert label_error_msg != ""
        assert well_error_msg != ""


@pytest.mark.asyncio
async def test_well_groupings_option_valid_inputs(user_logged_in_page):
    inputs = [("new name", "A1,B2,D3"), ("NewName", "A3,B3,C4")]
    add_grouping = await setUpWellGroupingsTest(user_logged_in_page)
    # test invalid inputs
    for index, input in enumerate(inputs):
        await add_grouping.click()
        # get inputs
        await user_logged_in_page.get_by_placeholder("Label Name").nth(index).fill(input[0])
        await user_logged_in_page.get_by_placeholder("A1, B2, C3").nth(index).fill(input[1])
        # get error msg
        label_error_components = await user_logged_in_page.query_selector_all("span#labelNameError")
        wells_error_components = await user_logged_in_page.query_selector_all("span#wellsError")
        current_label_error_components = label_error_components[index]
        current_wells_error_components = wells_error_components[index]
        label_error_msg = await current_label_error_components.evaluate("node=>node.innerHTML")
        well_error_msg = await current_wells_error_components.evaluate("node=>node.innerHTML")
        assert label_error_msg == ""
        assert well_error_msg == ""
