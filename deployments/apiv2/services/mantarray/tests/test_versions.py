import pytest
from random import choice, randint, shuffle

from .conftest import CLUSTER_NAME
from src.core import versions


def _random_semver():
    return f"{randint(0,1000)}.{randint(0,1000)}.{randint(0,1000)}"


def _shuffled_copy(items: list):
    items_copy = items.copy()
    shuffle(items_copy)
    return items_copy


def _get_test_main_fw_compatibility(include_channel_fw=False):
    # these must be in semver order
    ma_channel_fw_versions = ["1.1.0" "2.1.0", "3.1.0", "11.1.0"]
    ma_main_fw_versions = ["1.0.0", "2.0.0", "3.0.0", "11.0.0"]
    ma_sw_versions = ["1.0.1", "2.0.1", "3.0.1", "11.0.1"]
    sting_sw_versions = ["1" + ma_sw for ma_sw in ma_sw_versions]

    compat = [
        {
            "main_fw_version": main_fw,
            "min_ma_controller_version": ma_sw,
            "min_sting_controller_version": sting_sw,
        }
        for main_fw, ma_sw, sting_sw in zip(ma_main_fw_versions, ma_sw_versions, sting_sw_versions)
    ]
    if include_channel_fw:
        for compat_item, cfw in zip(compat, ma_channel_fw_versions):
            compat_item |= {"channel_fw_version": cfw}

    return compat


@pytest.mark.parametrize(
    "test_filter,expected_result",
    [
        (lambda v: v == "3.0.0", ["3.0.0"]),
        (lambda v: v <= "3.0.0", ["1.0.0", "1.0.1"]),
        (lambda v: v < "3.0.0", ["1.0.0", "1.0.1", "3.0.0"]),
        (lambda v: v > "10.0.0", ["11.0.0"]),
        (None, ["1.0.1", "11.0.0", "3.0.0", "1.0.0"]),
    ],
)
def test_filter_and_sort_semvers__returns_correct_values(test_filter, expected_result):
    test_versions = ["1.0.1", "11.0.0", "3.0.0", "1.0.0"]

    versions._filter_and_sort_semvers(test_versions, test_filter) == expected_result


def test_get_fw_download_url__generates_and_returns_presigned_using_the_params_given(mocker):
    mocked_generate = mocker.patch.object(versions, "generate_presigned_url", autospec=True)

    test_firmware_type = choice(["main", "channel"])
    test_version = choice(["1.11.111", "999.99.9"])

    assert versions.get_fw_download_url(test_version, test_firmware_type) == mocked_generate.return_value

    expected_bucket = f"{CLUSTER_NAME}-{test_firmware_type}-firmware"
    expected_key = f"{test_version}.bin"
    mocked_generate.assert_called_once_with(bucket=expected_bucket, key=expected_key)


def test_get_previous_sw_version__returns_correct_version_when_a_previous_version_exists():
    assert versions._get_previous_sw_version(["1.0.11", "1.1.0", "1.1.1", "11.0.0"], "2.0.0") == "1.1.1"


def test_get_previous_sw_version__returns_error_when_a_previous_version_does_not_exist():
    with pytest.raises(versions.NoPreviousSoftwareVersionError):
        versions._get_previous_sw_version(["1.0.11", "1.1.0", "1.1.1", "11.0.0"], "1.0.11")


def test_get_required_sw_version_range__returns_min_software_version_correctly(mocker):
    main_fw_compatibility = _get_test_main_fw_compatibility()

    test_idx = randint(0, len(main_fw_compatibility) - 1)
    expected_versions = main_fw_compatibility[test_idx]

    # patch since this doesn't matter for this test
    mocker.patch.object(versions, "_get_previous_sw_version", autospec=True)

    version_bounds = versions.get_required_sw_version_range(
        expected_versions["main_fw_version"], _shuffled_copy(main_fw_compatibility)
    )
    assert version_bounds["min_sw"] == f"{expected_versions['min_ma_controller_version']}-pre.0"
    assert version_bounds["min_sting_sw"] == f"{expected_versions['min_sting_controller_version']}-pre.0"


def test_get_required_sw_version_range__returns_max_sw_version_correctly__when_one_exists(mocker):
    main_fw_compatibility = _get_test_main_fw_compatibility()

    # last element will not have a max sw version
    test_idx = randint(0, len(main_fw_compatibility) - 2)

    mocked_prev_versions = [mocker.Mock()] * 2
    mocked_get_prev = mocker.patch.object(
        versions, "_get_previous_sw_version", autospec=True, side_effect=mocked_prev_versions
    )

    version_bounds = versions.get_required_sw_version_range(
        main_fw_compatibility[test_idx]["main_fw_version"], _shuffled_copy(main_fw_compatibility)
    )
    assert version_bounds["max_sw"] == f"{mocked_prev_versions[0]}-pre.0"
    assert version_bounds["max_sting_sw"] == f"{mocked_prev_versions[1]}-pre.0"

    assert mocked_get_prev.call_args_list == [
        mocker.call(mocker.ANY, main_fw_compatibility[test_idx + 1]["min_ma_controller_version"]),
        mocker.call(mocker.ANY, main_fw_compatibility[test_idx + 1]["min_sting_controller_version"]),
    ]


def test_get_required_sw_version_range__returns_max_sw_version_correctly__when_next_main_fw_has_same_sw_version(
    mocker,
):
    main_fw_compatibility = _get_test_main_fw_compatibility()

    test_idx = 0

    main_fw_compatibility[test_idx + 1] |= {
        key: main_fw_compatibility[test_idx][key]
        for key in ("min_ma_controller_version", "min_sting_controller_version")
    }

    mocked_prev_versions = [mocker.Mock()] * 2
    mocked_get_prev = mocker.patch.object(
        versions, "_get_previous_sw_version", autospec=True, side_effect=mocked_prev_versions
    )

    version_bounds = versions.get_required_sw_version_range(
        main_fw_compatibility[test_idx]["main_fw_version"], _shuffled_copy(main_fw_compatibility)
    )
    assert version_bounds["max_sw"] == f"{mocked_prev_versions[0]}-pre.0"
    assert version_bounds["max_sting_sw"] == f"{mocked_prev_versions[1]}-pre.0"

    assert mocked_get_prev.call_args_list == [
        mocker.call(mocker.ANY, main_fw_compatibility[test_idx + 2]["min_ma_controller_version"]),
        mocker.call(mocker.ANY, main_fw_compatibility[test_idx + 2]["min_sting_controller_version"]),
    ]


def test_get_required_sw_version_range__returns_max_sw_version_correctly__when_one_does_not_exist(mocker):
    main_fw_compatibility = _get_test_main_fw_compatibility()

    # only the final element will not have a max sw version
    expected_versions = main_fw_compatibility[-1]

    mocked_get_prev = mocker.patch.object(versions, "_get_previous_sw_version", autospec=True)

    version_bounds = versions.get_required_sw_version_range(
        expected_versions["main_fw_version"], _shuffled_copy(main_fw_compatibility)
    )
    assert version_bounds["max_sw"] == f"{expected_versions['min_ma_controller_version']}-pre.0"
    assert version_bounds["max_sting_sw"] == f"{expected_versions['min_sting_controller_version']}-pre.0"

    mocked_get_prev.assert_not_called()


def test_get_latest_compatible_versions__returns_item_with_highest_channel_fw_version():
    test_channel_fw_versions = ["1.2.3", "2.11.0", "10.0.0"]

    test_compatible_versions = [
        {"channel_fw_version": cfw} for cfw in _shuffled_copy(test_channel_fw_versions)
    ]

    assert versions.get_latest_compatible_versions(test_compatible_versions) == {
        "channel_fw_version": "10.0.0"
    }
