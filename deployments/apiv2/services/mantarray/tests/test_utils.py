import boto3 as mocked_boto3
import pytest
from random import choice

from immutabledict import immutabledict
from src import utils


def test_aws__get_db_secrets__returns_correct_values():
    # mock is performed in conftest.py
    assert utils.aws.get_db_secrets() == {
        "reader_endpoint": "reader_endpoint",
        "writer_endpoint": "writer_endpoint",
        "user": "user",
    }


def test_db__stores_aws_secrets_correctly():
    # utils.aws.get_db_secrets also mocked in conftest.py
    assert utils.db.DB_SECRETS_DICT == immutabledict(utils.aws.get_db_secrets())


def test_db__connection_pools_dict_is_created_correctly():
    assert utils.db.CONNECTION_POOLS == immutabledict(
        {
            "reader": utils.db.ThreadedConnectionPool.return_value,
            "writer": utils.db.ThreadedConnectionPool.return_value,
        }
    )
    utils.db.ThreadedConnectionPool.assert_any_call(
        1, 3, database="postgres", **utils.db.get_db_connect_info("reader")
    )
    utils.db.ThreadedConnectionPool.assert_any_call(
        1, 1, database="postgres", **utils.db.get_db_connect_info("writer")
    )


def test_db__get_cursor__return_function__gets_cursor_correct_from_thread_pool(mocker):
    reader_mock = mocker.MagicMock()
    writer_mock = mocker.MagicMock()
    mocker.patch.object(utils.db, "CONNECTION_POOLS", {"reader": reader_mock, "writer": writer_mock})

    reader_conn = reader_mock.getconn.return_value
    writer_conn = writer_mock.getconn.return_value

    # test reader first
    reader_cursor_gen = utils.db.get_cursor("reader")
    next(reader_cursor_gen())
    # make sure reader was accessed
    reader_mock.getconn.assert_called_once_with()
    reader_conn.cursor.assert_called_once_with(cursor_factory=utils.db.DictCursor)
    # make sure writer wasn't accessed
    writer_mock.getconn.assert_not_called()
    writer_conn.cursor.assert_not_called()
    # test writer
    writer_cursor_gen = utils.db.get_cursor("writer")
    next(writer_cursor_gen())
    # make sure reader wasn't accessed again
    reader_mock.getconn.assert_called_once_with()
    reader_conn.cursor.assert_called_once_with(cursor_factory=utils.db.DictCursor)
    # make sure writer was accessed
    writer_mock.getconn.assert_called_once_with()
    writer_conn.cursor.assert_called_once_with(cursor_factory=utils.db.DictCursor)


def test_db__get_cursor__return_function__closes_cursor(mocker):
    reader_mock = mocker.MagicMock()
    writer_mock = mocker.MagicMock()
    mocker.patch.object(utils.db, "CONNECTION_POOLS", {"reader": reader_mock, "writer": writer_mock})

    # arbitrarily choosing to use reader pool for this test
    reader_conn = reader_mock.getconn.return_value
    reader_cursor = reader_conn.cursor.return_value

    reader_cursor_gen = utils.db.get_cursor("reader")
    next(reader_cursor_gen())

    reader_cursor.close.assert_called_once_with()


def test_db__get_cursor__return_function__releases_db_connection(mocker):
    reader_mock = mocker.MagicMock()
    writer_mock = mocker.MagicMock()
    mocker.patch.object(utils.db, "CONNECTION_POOLS", {"reader": reader_mock, "writer": writer_mock})

    # arbitrarily choosing to use writer pool for this test
    writer_conn = writer_mock.getconn.return_value

    writer_cursor_gen = utils.db.get_cursor("writer")
    next(writer_cursor_gen())

    writer_mock.putconn.assert_called_once_with(writer_conn)


def test_firmware__create_dependency_mapping__gets_firmware_file_objects_from_s3_correctly():
    mocked_s3_client = mocked_boto3.client("s3")
    mocked_s3_client.list_objects.return_value = {"Contents": []}

    utils.firmware.create_dependency_mapping()

    assert mocked_s3_client.list_objects.call_count == 3
    mocked_s3_client.list_objects.assert_any_call(Bucket="channel-firmware")
    mocked_s3_client.list_objects.assert_any_call(Bucket="main-firmware")


def test_firmware__create_dependency_mapping__retrieves_metadata_of_each_appropriately_named_firmware_file_in_s3_bucket_correctly(
    mocker,
):
    mocked_s3_client = mocked_boto3.client("s3")

    expected_main_bucket_name = "main-firmware"
    expected_channel_bucket_name = "channel-firmware"

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

    utils.firmware.create_dependency_mapping()

    expected_calls = [
        mocker.call(Bucket=expected_channel_bucket_name, Key=file_name)
        for file_name in expected_valid_channel_file_names
    ] * 2
    expected_calls.extend(
        [
            mocker.call(Bucket=expected_main_bucket_name, Key=file_name)
            for file_name in expected_valid_main_file_names
        ]
    )
    assert mocked_s3_client.head_object.call_args_list == expected_calls


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
    assert utils.firmware.get_cfw_from_hw(test_cfw_to_hw, hw_version) == channel_fw_version


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
        utils.firmware, "get_cfw_from_hw", autospec=True, side_effect=get_cfw_from_hw_se
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
        utils.firmware,
        "create_dependency_mapping",
        autospec=True,
        return_value=(dummy_cfw_to_hw, test_cfw_to_mfw, test_main_fw_to_sw),
    )

    assert utils.firmware.resolve_versions(hw_version) == {
        "sw": sw_version,
        "main-fw": main_fw_version,
        "channel-fw": channel_fw_version,
    }
    mocked_get_cfw_from_hw.assert_called_once_with(dummy_cfw_to_hw, hw_version)


def test__firmware__get_download_url__generates_and_returns_presigned_url_if_params_are_valid():
    mocked_s3_client = mocked_boto3.client("s3")

    test_firmware_type = choice(["main", "channel"])
    test_version = choice(["1.11.111", "999.99.9"])

    assert (
        utils.firmware.get_download_url(test_version, test_firmware_type)
        == mocked_s3_client.generate_presigned_url.return_value
    )
    mocked_s3_client.generate_presigned_url.assert_called_once_with(
        ClientMethod="get_object",
        Params={"Bucket": f"{test_firmware_type}-firmware", "Key": f"{test_version}.bin"},
        ExpiresIn=3600,
    )


def test__firmware__get_download_url__returns_none_if_presigned_url_generation_fails():
    mocked_s3_client = mocked_boto3.client("s3")
    mocked_s3_client.generate_presigned_url.side_effect = Exception

    test_firmware_type = "any"
    test_version = "any"

    assert utils.firmware.get_download_url(test_version, test_firmware_type) is None
