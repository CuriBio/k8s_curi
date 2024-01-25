import pytest
from random import choice, randint, shuffle

from .conftest import CLUSTER_NAME
from src.core import versions


def _random_semver():
    return f"{randint(0,1000)}.{randint(0,1000)}.{randint(0,1000)}"


def _shuffled_copy(items: list | dict):
    if isinstance(items, list):
        items_copy = items.copy()
        shuffle(items_copy)
    elif isinstance(items, dict):
        keys = list(items.keys())
        shuffle(keys)
        items_copy = {k: items[k] for k in keys}

    return items_copy


def _get_test_main_fw_compatibility(include_channel_fw=False):
    # these must be in semver order
    ma_channel_fw_versions = ["1.1.0", "2.1.0", "3.1.0", "11.1.0"]
    ma_main_fw_versions = ["1.0.0", "2.0.0", "3.0.0", "11.0.0"]

    ma_sw_versions = [
        {"version": v, "state": "external" if i % 2 == 0 else "internal"}
        for i, v in enumerate(["1.0.1", "1.1.1", "2.0.1", "2.1.1", "3.0.1", "3.1.1", "11.0.1", "11.1.1"])
    ]
    min_ma_sw_versions = [d["version"] for d in ma_sw_versions if d["state"] == "external"]

    sting_sw_versions = [{"version": "1" + d["version"], "state": d["state"]} for d in ma_sw_versions]
    # sting_sw_versions = [{"1" + v: state for v, state in ma_sw_versions.items()}]
    min_sting_sw_versions = [d["version"] for d in sting_sw_versions if d["state"] == "external"]

    main_fw_compatibility = [
        {
            "main_fw_version": main_fw,
            "min_ma_controller_version": ma_sw,
            "min_sting_controller_version": sting_sw,
        }
        for main_fw, ma_sw, sting_sw in zip(ma_main_fw_versions, min_ma_sw_versions, min_sting_sw_versions)
    ]
    if include_channel_fw:
        for compat_item, cfw in zip(main_fw_compatibility, ma_channel_fw_versions):
            compat_item |= {"channel_fw_version": cfw}

    return (main_fw_compatibility, ma_sw_versions, sting_sw_versions)


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
    assert versions._get_previous_sw_version(["1.0.11", "1.1.0", "1.1.1", "11.0.0"], "11.0.0") == "1.1.1"
    assert versions._get_previous_sw_version(["1.0.11", "1.1.0", "1.1.1", "11.0.0"], "2.0.0") == "1.1.1"


def test_get_previous_sw_version__returns_error_when_a_previous_version_does_not_exist():
    with pytest.raises(versions.NoPreviousSoftwareVersionError):
        versions._get_previous_sw_version(["1.0.11", "1.1.0", "1.1.1", "11.0.0"], "1.0.11")


@pytest.mark.parametrize("remove_internal", [True, False])
def test_get_required_sw_version_range__returns_min_software_version_correctly(mocker, remove_internal):
    main_fw_compatibility, ma_sw_versions, sting_sw_versions = _get_test_main_fw_compatibility()

    test_idx = randint(0, len(main_fw_compatibility) - 1)
    expected_versions = main_fw_compatibility[test_idx]

    # patch since this doesn't matter for this test
    mocker.patch.object(versions, "_get_previous_sw_version", autospec=True)

    version_bounds = versions.get_required_sw_version_range(
        expected_versions["main_fw_version"],
        _shuffled_copy(main_fw_compatibility),
        _shuffled_copy(ma_sw_versions),
        _shuffled_copy(sting_sw_versions),
        remove_internal,
    )
    assert version_bounds["min_sw"] == f"{expected_versions['min_ma_controller_version']}-pre.0"
    assert version_bounds["min_sting_sw"] == f"{expected_versions['min_sting_controller_version']}-pre.0"


@pytest.mark.parametrize("remove_internal", [True, False])
def test_get_required_sw_version_range__returns_max_sw_version_correctly__when_one_exists(
    mocker, remove_internal
):
    main_fw_compatibility, ma_sw_versions, sting_sw_versions = _get_test_main_fw_compatibility()

    # last element will not have a max sw version
    test_idx = randint(0, len(main_fw_compatibility) - 2)

    expected_sw_idx = test_idx * 2
    if not remove_internal:
        expected_sw_idx += 1

    spied_get_prev = mocker.spy(versions, "_get_previous_sw_version")

    version_bounds = versions.get_required_sw_version_range(
        main_fw_compatibility[test_idx]["main_fw_version"],
        _shuffled_copy(main_fw_compatibility),
        _shuffled_copy(ma_sw_versions),
        _shuffled_copy(sting_sw_versions),
        remove_internal,
    )
    assert version_bounds["max_sw"] == ma_sw_versions[expected_sw_idx]["version"]
    assert version_bounds["max_sting_sw"] == sting_sw_versions[expected_sw_idx]["version"]

    assert spied_get_prev.call_args_list == [
        mocker.call(mocker.ANY, main_fw_compatibility[test_idx + 1]["min_ma_controller_version"]),
        mocker.call(mocker.ANY, main_fw_compatibility[test_idx + 1]["min_sting_controller_version"]),
    ]


@pytest.mark.parametrize("remove_internal", [True, False])
def test_get_required_sw_version_range__returns_max_sw_version_correctly__when_next_main_fw_has_same_sw_version(
    mocker, remove_internal
):
    main_fw_compatibility, ma_sw_versions, sting_sw_versions = _get_test_main_fw_compatibility()

    test_idx = 0

    main_fw_compatibility[test_idx + 1] |= {
        key: main_fw_compatibility[test_idx][key]
        for key in ("min_ma_controller_version", "min_sting_controller_version")
    }

    expected_sw_idx = test_idx * 2 + 2
    if not remove_internal:
        expected_sw_idx += 1

    spied_get_prev = mocker.spy(versions, "_get_previous_sw_version")

    version_bounds = versions.get_required_sw_version_range(
        main_fw_compatibility[test_idx]["main_fw_version"],
        _shuffled_copy(main_fw_compatibility),
        _shuffled_copy(ma_sw_versions),
        _shuffled_copy(sting_sw_versions),
        remove_internal,
    )
    assert version_bounds["max_sw"] == ma_sw_versions[expected_sw_idx]["version"]
    assert version_bounds["max_sting_sw"] == sting_sw_versions[expected_sw_idx]["version"]

    assert spied_get_prev.call_args_list == [
        mocker.call(mocker.ANY, main_fw_compatibility[test_idx + 2]["min_ma_controller_version"]),
        mocker.call(mocker.ANY, main_fw_compatibility[test_idx + 2]["min_sting_controller_version"]),
    ]


@pytest.mark.parametrize("remove_internal", [True, False])
def test_get_required_sw_version_range__returns_max_sw_version_correctly__when_one_does_not_exist(
    mocker, remove_internal
):
    main_fw_compatibility, ma_sw_versions, sting_sw_versions = _get_test_main_fw_compatibility()

    # only the final element will not have a max sw version
    test_fw_version = main_fw_compatibility[-1]["main_fw_version"]

    expected_final_idx = -2 if remove_internal else -1

    spied_get_prev = mocker.patch.object(versions, "_get_previous_sw_version")

    version_bounds = versions.get_required_sw_version_range(
        test_fw_version,
        _shuffled_copy(main_fw_compatibility),
        _shuffled_copy(ma_sw_versions),
        _shuffled_copy(sting_sw_versions),
        remove_internal,
    )
    assert version_bounds["max_sw"] == ma_sw_versions[expected_final_idx]["version"]
    assert version_bounds["max_sting_sw"] == sting_sw_versions[expected_final_idx]["version"]

    spied_get_prev.assert_not_called()


def test_get_latest_compatible_versions__returns_item_with_highest_channel_fw_version():
    test_channel_fw_versions = ["1.2.3", "2.11.0", "10.0.0"]

    test_compatible_versions = [
        {"channel_fw_version": cfw} for cfw in _shuffled_copy(test_channel_fw_versions)
    ]

    assert versions.get_latest_compatible_versions(test_compatible_versions) == {
        "channel_fw_version": "10.0.0"
    }
