import pytest
from random import choice, randint

from .conftest import CLUSTER_NAME
from src.core import versions
from src.core.versions import SOFTWARE_INSTALLER_PREFIX, DOWNLOADS_BUCKET_NAME


def random_semver():
    return f"{randint(0,1000)}.{randint(0,1000)}.{randint(0,1000)}"


@pytest.fixture(scope="function", name="mocked_boto3", autouse=True)
def fixture_mocked_boto3(mocker):
    yield mocker.patch.object(versions, "boto3", autospec=True)


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

    versions.filter_and_sort_semvers(test_versions, test_filter) == expected_result


def test_create_dependency_mapping__lists_firmware_file_objects_from_s3_correctly(mocked_boto3):
    mocked_s3_client = mocked_boto3.client("s3")
    mocked_s3_client.list_objects.return_value = {"Contents": []}

    versions.create_dependency_mapping()

    assert mocked_s3_client.list_objects.call_count == 3
    mocked_s3_client.list_objects.assert_any_call(Bucket=f"{CLUSTER_NAME}-channel-firmware")
    mocked_s3_client.list_objects.assert_any_call(Bucket=f"{CLUSTER_NAME}-main-firmware")


def test_create_dependency_mapping__retrieves_metadata_of_each_appropriately_named_firmware_file_in_s3_bucket_correctly(
    mocked_boto3,
):
    mocked_s3_client = mocked_boto3.client("s3")

    expected_main_bucket_name = f"{CLUSTER_NAME}-main-firmware"
    expected_channel_bucket_name = f"{CLUSTER_NAME}-channel-firmware"

    expected_valid_main_file_names = ["0.0.0.bin", "99.99.99.bin"]
    expected_valid_channel_file_names = ["0.9.9.bin", "99.88.0.bin"]

    def lo_se(Bucket):
        test_file_names = [
            "x1.0.0.bin",
            "x.0.0.bin",
            "1.x.0.bin",
            "1.0.x.bin",
            "1.0.0,bin",
            "1.0.0.bit",
            "1.0.0.binx",
        ]
        if Bucket == expected_main_bucket_name:
            test_file_names.extend(expected_valid_main_file_names)
        else:
            test_file_names.extend(expected_valid_channel_file_names)
        return {"Contents": [{"Key": file_name} for file_name in test_file_names]}

    mocked_s3_client.list_objects.side_effect = lo_se

    mocked_s3_client.head_object.side_effect = lambda Bucket, Key: {
        "Metadata": (
            {"sw-version": "0.0.0"}
            if Bucket == expected_main_bucket_name
            else {"main-fw-version": "0.0.0", "hw-version": "0.0.0"}
        )
    }

    versions.create_dependency_mapping()

    for file_list, bucket_name in (
        (expected_valid_channel_file_names, expected_channel_bucket_name),
        (expected_valid_main_file_names, expected_main_bucket_name),
    ):
        for file_name in file_list:
            mocked_s3_client.head_object.assert_any_call(Bucket=bucket_name, Key=file_name)


def test_create_dependency_mapping__returns_correct_mappings(mocked_boto3):
    mocked_s3_client = mocked_boto3.client("s3")

    expected_main_bucket_name = f"{CLUSTER_NAME}-main-firmware"

    expected_main_objs_and_metadata = {
        "1.0.1.bin": {"sw-version": "1.0.0"},
        "2.0.2.bin": {"sw-version": "2.0.0"},
    }
    expected_channel_objs_and_metadata = {
        "1.1.0.bin": {"main-fw-version": "1.0.1", "hw-version": "1.1.1"},
        "2.2.0.bin": {"main-fw-version": "2.0.2", "hw-version": "2.2.2"},
    }

    def get_s3_objs(bucket):
        return (
            expected_main_objs_and_metadata
            if bucket == expected_main_bucket_name
            else expected_channel_objs_and_metadata
        )

    mocked_s3_client.list_objects.side_effect = lambda Bucket: {
        "Contents": [{"Key": file_name} for file_name in get_s3_objs(Bucket)]
    }
    mocked_s3_client.head_object.side_effect = lambda Bucket, Key: {"Metadata": get_s3_objs(Bucket)[Key]}

    cfw_to_hw, cfw_to_mfw, mfw_to_sw = versions.create_dependency_mapping()
    assert cfw_to_hw == {"1.1.0": "1.1.1", "2.2.0": "2.2.2"}
    assert cfw_to_mfw == {"1.1.0": "1.0.1", "2.2.0": "2.0.2"}
    assert mfw_to_sw == {"1.0.1": "1.0.0", "2.0.2": "2.0.0"}


@pytest.mark.parametrize(
    "channel_fw_version,hw_version",
    [("1.0.0", "1.0.0"), ("3.0.0", "2.0.0"), ("4.0.0", "3.0.0"), ("5.0.0", "4.0.0"), ("11.0.0", "10.0.0")],
)
def test_get_cfw_from_hw__returns_correct_values(channel_fw_version, hw_version):
    test_cfw_to_hw = {
        "1.0.0": "2.0.0",
        "2.0.0": "2.0.0",
        "3.0.0": "2.0.0",
        "4.0.0": "3.0.0",
        "5.0.0": "4.0.0",
        "11.0.0": "11.0.0",
    }
    assert versions.get_cfw_from_hw(test_cfw_to_hw, hw_version) == channel_fw_version


@pytest.mark.parametrize(
    "hw_version,channel_fw_version,main_fw_version,sw_version",
    [
        ("1.0.0", "3.0.0", "3.0.0", "2.0.0"),
        ("2.0.0", "4.0.0", "4.0.0", "2.0.0"),
        ("3.0.0", "5.0.0", "6.0.0", "5.0.0"),
    ],
)
def test_resolve_versions__return_correct_dict(
    hw_version, channel_fw_version, main_fw_version, sw_version, mocker
):
    def get_cfw_from_hw_se(cfw_to_hw, hardware_version):
        test_hw_to_cfw = {"1.0.0": "3.0.0", "2.0.0": "4.0.0", "3.0.0": "5.0.0"}
        return test_hw_to_cfw[hardware_version]

    mocked_get_cfw_from_hw = mocker.patch.object(
        versions, "get_cfw_from_hw", autospec=True, side_effect=get_cfw_from_hw_se
    )

    dummy_cfw_to_hw = "cfw_to_hw"
    test_cfw_to_mfw = {
        "1.0.0": "1.0.0",
        "2.0.0": "2.0.0",
        "3.0.0": "3.0.0",
        "4.0.0": "4.0.0",
        "5.0.0": "6.0.0",
    }
    test_main_fw_to_sw = {
        "1.0.0": "1.0.0",
        "2.0.0": "2.0.0",
        "3.0.0": "2.0.0",
        "4.0.0": "2.0.0",
        "5.0.0": "3.0.0",
        "6.0.0": "5.0.0",
    }
    mocker.patch.object(
        versions,
        "create_dependency_mapping",
        autospec=True,
        return_value=(dummy_cfw_to_hw, test_cfw_to_mfw, test_main_fw_to_sw),
    )

    assert versions.resolve_versions(hw_version) == {
        "sw": sw_version,
        "main-fw": main_fw_version,
        "channel-fw": channel_fw_version,
    }
    mocked_get_cfw_from_hw.assert_called_once_with(dummy_cfw_to_hw, hw_version)


def test_get_download_url__generates_and_returns_presigned_using_the_params_given(mocker):
    mocked_generate = mocker.patch.object(versions, "generate_presigned_url", autospec=True)

    test_firmware_type = choice(["main", "channel"])
    test_version = choice(["1.11.111", "999.99.9"])

    assert versions.get_download_url(test_version, test_firmware_type) == mocked_generate.return_value

    expected_bucket = f"{CLUSTER_NAME}-{test_firmware_type}-firmware"
    expected_key = f"{test_version}.bin"
    mocked_generate.assert_called_once_with(bucket=expected_bucket, key=expected_key)


def test_get_all_sw_versions__lists_and_returns_software_installer_objects_from_s3_correctly(mocked_boto3):
    mocked_s3_client = mocked_boto3.client("s3")

    expected_software_versions = {"1.0.11", "1.1.0", "1.1.1"}

    test_files_in_bucket = [
        *[f"{SOFTWARE_INSTALLER_PREFIX}-{version}.exe" for version in expected_software_versions],
        "Not an installer",
        f"{SOFTWARE_INSTALLER_PREFIX}-8.8.8.exe.blockmap",
        "software/MantarrayController-Setup-unstable-9.9.9.exe",
        "software/MantarrayController-Setup-unstable-1.1.0-pre.123.exe",
    ]

    mocked_s3_client.list_objects.side_effect = lambda Bucket, Prefix: {
        "Contents": [{"Key": file_name} for file_name in test_files_in_bucket if file_name.startswith(Prefix)]
    }

    actual_versions = versions.get_all_sw_versions()

    assert set(actual_versions) == expected_software_versions
    mocked_s3_client.list_objects.assert_called_once_with(
        Bucket=DOWNLOADS_BUCKET_NAME, Prefix=SOFTWARE_INSTALLER_PREFIX
    )


def test_get_previous_sw_version__returns_correct_version_when_a_previous_version_exists():
    assert versions.get_previous_software_version(["1.0.11", "1.1.0", "1.1.1", "11.0.0"], "2.0.0") == "1.1.1"


def test_get_previous_sw_version__returns_error_when_a_previous_version_does_not_exist():
    with pytest.raises(versions.NoPreviousSoftwareVersionError):
        versions.get_previous_software_version(["1.0.11", "1.1.0", "1.1.1", "11.0.0"], "1.0.11")


def test_get_latest_software_version__returns_latest_version():
    assert versions.get_latest_software_version(["1.0.11", "1.1.0", "1.1.1", "11.0.0"]) == "11.0.0"


def test_get_required_sw_version_range__returns_min_software_version_correctly(mocker):
    mocked_cdm = mocker.patch.object(versions, "create_dependency_mapping", autospec=True)
    mfw_to_sw = {"1.0.0": "1.0.1", "2.0.0": "2.0.1", "3.0.0": "3.0.1", "11.0.0": "11.0.1"}
    mocked_cdm.return_value = ({}, {}, mfw_to_sw)

    # only patching in this test to avoid errors
    mocker.patch.object(versions, "get_all_sw_versions", autospec=True, return_value=[])
    mocker.patch.object(versions, "get_previous_software_version", autospec=True)

    test_mfw_version = "3.0.0"
    assert versions.get_required_sw_version_range(test_mfw_version)["min_sw"] == mfw_to_sw[test_mfw_version]

    mocked_cdm.assert_called_once_with()


def test_get_required_sw_version_range__returns_max_sw_version_correctly__when_one_exists(mocker):
    mocked_cdm = mocker.patch.object(versions, "create_dependency_mapping", autospec=True)
    mfw_to_sw = {"1.0.0": "1.0.1", "2.0.0": "2.0.1", "3.0.0": "3.0.1", "22.0.0": "22.0.1"}
    mocked_cdm.return_value = ({}, {}, mfw_to_sw)

    mocked_get_all = mocker.patch.object(versions, "get_all_sw_versions", autospec=True)
    mocked_get_prev = mocker.patch.object(versions, "get_previous_software_version", autospec=True)

    assert versions.get_required_sw_version_range("2.0.0")["max_sw"] == mocked_get_prev.return_value

    mocked_get_prev.assert_called_once_with(mocked_get_all.return_value, "3.0.1")


def test_get_required_sw_version_range__returns_max_sw_version_correctly__when_next_main_fw_has_same_sw_version(
    mocker,
):
    mocked_cdm = mocker.patch.object(versions, "create_dependency_mapping", autospec=True)
    mfw_to_sw = {"1.0.0": "1.0.1", "2.0.0": "1.0.1", "3.0.0": "3.0.1", "11.0.0": "11.0.1"}
    mocked_cdm.return_value = ({}, {}, mfw_to_sw)

    mocked_get_all = mocker.patch.object(versions, "get_all_sw_versions", autospec=True)
    mocked_get_prev = mocker.patch.object(versions, "get_previous_software_version", autospec=True)

    assert versions.get_required_sw_version_range("1.0.0")["max_sw"] == mocked_get_prev.return_value

    mocked_get_prev.assert_called_once_with(mocked_get_all.return_value, "3.0.1")


def test_get_required_sw_version_range__returns_max_sw_version_correctly__when_one_does_not_exist(mocker):
    mocked_cdm = mocker.patch.object(versions, "create_dependency_mapping", autospec=True)
    mfw_to_sw = {"1.0.0": "1.0.1", "2.0.0": "2.0.1", "3.0.0": "3.0.1", "11.0.0": "11.0.1"}
    mocked_cdm.return_value = ({}, {}, mfw_to_sw)

    mocked_get_prev = mocker.patch.object(versions, "get_previous_software_version", autospec=True)

    expected_version = "2.3.4"
    mocker.patch.object(versions, "get_all_sw_versions", autospec=True, return_value=[expected_version])

    assert versions.get_required_sw_version_range("11.0.0")["max_sw"] == expected_version

    mocked_get_prev.assert_not_called()
