import re

import boto3
from semver import VersionInfo

from .config import CLUSTER_NAME


FIRMWARE_FILE_REGEX = re.compile(r"^\d+\.\d+\.\d+\.bin$")


def create_dependency_mapping():
    """Create depency mappings of SW/FW/HW versions as a dict.

    Mappings include:
        - Channel FW -> HW
        - Channel FW -> Main FW
        - Main FW -> SW
    """
    s3_client = boto3.client("s3")

    # create dependency mappings
    cfw_to_hw = {}
    cfw_to_mfw = {}
    mfw_to_sw = {}
    for bucket, metadata_prefix, dependency_mapping in (
        ("channel-firmware", "hw", cfw_to_hw),
        ("channel-firmware", "main-fw", cfw_to_mfw),
        ("main-firmware", "sw", mfw_to_sw),
    ):
        bucket = f"{CLUSTER_NAME}-{bucket}"
        firmware_file_objs = s3_client.list_objects(Bucket=bucket)
        # create list of all objects in bucket with a valid file name
        firmware_file_names = [
            item["Key"] for item in firmware_file_objs["Contents"] if FIRMWARE_FILE_REGEX.search(item["Key"])
        ]
        for file_name in firmware_file_names:
            head_obj = s3_client.head_object(Bucket=bucket, Key=file_name)
            # get version from object metadata
            metadata_key = f"{metadata_prefix}-version"
            metadata_version = head_obj["Metadata"][metadata_key]
            # get version of object and add entry to mapping
            obj_version = file_name.split(".bin")[0]
            dependency_mapping[obj_version] = metadata_version
    return cfw_to_hw, cfw_to_mfw, mfw_to_sw


def get_cfw_from_hw(cfw_to_hw, device_hw_version):
    device_hw_version = VersionInfo.parse(device_hw_version)
    cfw_to_hw = {VersionInfo.parse(cfw): VersionInfo.parse(hw) for cfw, hw in cfw_to_hw.items()}
    try:
        cfw_version = sorted(cfw for cfw, hw in cfw_to_hw.items() if hw == device_hw_version)[-1]
    except IndexError:
        cfw_version = sorted(cfw for cfw, hw in cfw_to_hw.items() if device_hw_version < hw)[0]
    return str(cfw_version)


def resolve_versions(hardware_version):
    cfw_to_hw, cfw_to_mfw, mfw_to_sw = create_dependency_mapping()
    cfw = get_cfw_from_hw(cfw_to_hw, hardware_version)
    mfw = cfw_to_mfw[cfw]
    sw = mfw_to_sw[mfw]
    return {"sw": sw, "main-fw": mfw, "channel-fw": cfw}


def get_download_url(version, firmware_type):
    s3_client = boto3.client("s3")

    bucket = f"{CLUSTER_NAME}-{firmware_type}-firmware"
    file_name = f"{version}.bin"
    # TODO use core.lib.utils.generate_presigned_url here instead
    url = s3_client.generate_presigned_url(
        ClientMethod="get_object", Params={"Bucket": bucket, "Key": file_name}, ExpiresIn=3600
    )
    return url
