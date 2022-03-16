import os
import re


import boto3
from semver import VersionInfo

# TODO figure out how to handle this
S3_MAIN_BUCKET = os.environ.get("S3_MAIN_BUCKET")
S3_CHANNEL_BUCKET = os.environ.get("S3_CHANNEL_BUCKET")
FIRMWARE_FILE_REGEX = re.compile(r"^\d+\.\d+\.\d+\.bin$")


def get_cfw_from_hw(cfw_to_hw, current_hw_version):
    current_hw_version_info = VersionInfo.parse(current_hw_version)
    cfw_to_hw = {VersionInfo.parse(key): VersionInfo.parse(val) for key, val in cfw_to_hw.items()}
    try:
        cfw_version_info = sorted(cfw for cfw, hw in cfw_to_hw.items() if hw == current_hw_version_info)[-1]
    except IndexError:
        cfw_version_info = sorted(cfw for cfw, hw in cfw_to_hw.items() if current_hw_version_info < hw)[0]
    return str(cfw_version_info)


def create_dependency_mapping():
    s3_client = boto3.client("s3")

    # create dependency mappings
    cfw_to_hw = {}
    cfw_to_mfw = {}
    mfw_to_sw = {}
    for bucket, metadata_prefix, dependency_mapping in (
        (S3_CHANNEL_BUCKET, "hw", cfw_to_hw),
        (S3_CHANNEL_BUCKET, "main-fw", cfw_to_mfw),
        (S3_MAIN_BUCKET, "sw", mfw_to_sw),
    ):
        firmware_bucket_objs = s3_client.list_objects(Bucket=bucket)
        firmware_file_names = [
            item["Key"]
            for item in firmware_bucket_objs["Contents"]
            if FIRMWARE_FILE_REGEX.search(item["Key"])
        ]
        for file_name in firmware_file_names:
            head_obj = s3_client.head_object(Bucket=bucket, Key=file_name)
            dependent_version = head_obj["Metadata"][f"{metadata_prefix}-version"]
            dependency_mapping[file_name.split(".bin")[0]] = dependent_version
    return cfw_to_hw, cfw_to_mfw, mfw_to_sw


def resolve_versions(cfw_to_hw, cfw_to_mfw, mfw_to_sw, hardware_version):
    cfw = get_cfw_from_hw(cfw_to_hw, hardware_version)
    mfw = cfw_to_mfw[cfw]
    sw = mfw_to_sw[mfw]
    return {"sw": sw, "main-fw": mfw, "channel-fw": cfw}


def get_latest_firmware_version(hardware_version):
    cfw_to_hw, cfw_to_mfw, mfw_to_sw = create_dependency_mapping()
    try:
        return resolve_versions(cfw_to_hw, cfw_to_mfw, mfw_to_sw, hardware_version)
    except:
        return None


def get_download_url(version, firmware_type):
    s3_client = boto3.client("s3")

    bucket = S3_MAIN_BUCKET if firmware_type == "main" else S3_CHANNEL_BUCKET
    file_name = f"{version}.bin"
    try:
        return s3_client.generate_presigned_url(
            ClientMethod="get_object", Params={"Bucket": bucket, "Key": file_name}, ExpiresIn=3600
        )
    except:
        return None
