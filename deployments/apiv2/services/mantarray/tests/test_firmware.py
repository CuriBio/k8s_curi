import boto3 as mocked_boto3
import pytest
from random import choice

from .conftest import CLUSTER_NAME
from src.core import firmware


def test_firmware__create_dependency_mapping__gets_firmware_file_objects_from_s3_correctly():
    mocked_s3_client = mocked_boto3.client("s3")
    mocked_s3_client.list_objects.return_value = {"Contents": []}

    firmware.create_dependency_mapping()

    assert mocked_s3_client.list_objects.call_count == 3
    mocked_s3_client.list_objects.assert_any_call(Bucket=f"{CLUSTER_NAME}-channel-firmware")
    mocked_s3_client.list_objects.assert_any_call(Bucket=f"{CLUSTER_NAME}-main-firmware")


def test_firmware__create_dependency_mapping__retrieves_metadata_of_each_appropriately_named_firmware_file_in_s3_bucket_correctly(
    mocker,
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

    firmware.create_dependency_mapping()

    for file_list, bucket_name in (
        (expected_valid_channel_file_names, expected_channel_bucket_name),
        (expected_valid_main_file_names, expected_main_bucket_name),
    ):
        for file_name in file_list:
            mocked_s3_client.head_object.assert_any_call(Bucket=bucket_name, Key=file_name)


def test_firmware__create_dependency_mapping__returns_correct_mappings(
    mocker,
):
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

    def lo_se(Bucket):
        objs = (
            expected_main_objs_and_metadata
            if Bucket == expected_main_bucket_name
            else expected_channel_objs_and_metadata
        )
        test_file_names = list(objs.keys())
        return {"Contents": [{"Key": file_name} for file_name in test_file_names]}

    mocked_s3_client.list_objects.side_effect = lo_se

    def ho_se(Bucket, Key):
        objs = (
            expected_main_objs_and_metadata
            if Bucket == expected_main_bucket_name
            else expected_channel_objs_and_metadata
        )
        return {"Metadata": objs[Key]}

    mocked_s3_client.head_object.side_effect = ho_se

    cfw_to_hw, cfw_to_mfw, mfw_to_sw = firmware.create_dependency_mapping()
    assert cfw_to_hw == {"1.1.0": "1.1.1", "2.2.0": "2.2.2"}
    assert cfw_to_mfw == {"1.1.0": "1.0.1", "2.2.0": "2.0.2"}
    assert mfw_to_sw == {"1.0.1": "1.0.0", "2.0.2": "2.0.0"}


@pytest.mark.parametrize(
    "hw_version,channel_fw_version",
    [("1.0.0", "1.0.0"), ("2.0.0", "3.0.0"), ("3.0.0", "4.0.0"), ("4.0.0", "5.0.0")],
)
def test_firmware__get_cfw_from_hw__returns_correct_values(hw_version, channel_fw_version):
    test_cfw_to_hw = {
        "1.0.0": "1.0.0",
        "1.0.0": "2.0.0",
        "2.0.0": "2.0.0",
        "3.0.0": "2.0.0",
        "4.0.0": "3.0.0",
        "5.0.0": "4.0.0",
    }
    assert firmware.get_cfw_from_hw(test_cfw_to_hw, hw_version) == channel_fw_version


@pytest.mark.parametrize(
    "hw_version,channel_fw_version,main_fw_version,sw_version",
    [
        ("1.0.0", "3.0.0", "3.0.0", "2.0.0"),
        ("2.0.0", "4.0.0", "4.0.0", "2.0.0"),
        ("3.0.0", "5.0.0", "6.0.0", "5.0.0"),
    ],
)
def test_firmware__resolve_versions__return_correct_dict(
    hw_version, channel_fw_version, main_fw_version, sw_version, mocker
):
    def get_cfw_from_hw_se(cfw_to_hw, hardware_version):
        test_hw_to_cfw = {"1.0.0": "3.0.0", "2.0.0": "4.0.0", "3.0.0": "5.0.0"}
        return test_hw_to_cfw[hardware_version]

    mocked_get_cfw_from_hw = mocker.patch.object(
        firmware, "get_cfw_from_hw", autospec=True, side_effect=get_cfw_from_hw_se
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
        firmware,
        "create_dependency_mapping",
        autospec=True,
        return_value=(dummy_cfw_to_hw, test_cfw_to_mfw, test_main_fw_to_sw),
    )

    assert firmware.resolve_versions(hw_version) == {
        "sw": sw_version,
        "main-fw": main_fw_version,
        "channel-fw": channel_fw_version,
    }
    mocked_get_cfw_from_hw.assert_called_once_with(dummy_cfw_to_hw, hw_version)


def test__firmware__get_download_url__generates_and_returns_presigned_using_the_params_given():
    mocked_s3_client = mocked_boto3.client("s3")

    test_firmware_type = choice(["main", "channel"])
    test_version = choice(["1.11.111", "999.99.9"])

    assert (
        firmware.get_download_url(test_version, test_firmware_type)
        == mocked_s3_client.generate_presigned_url.return_value
    )
    mocked_s3_client.generate_presigned_url.assert_called_once_with(
        ClientMethod="get_object",
        Params={"Bucket": f"{CLUSTER_NAME}-{test_firmware_type}-firmware", "Key": f"{test_version}.bin"},
        ExpiresIn=3600,
    )
