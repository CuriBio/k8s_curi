import re

import boto3
from semver import VersionInfo

from .config import CLUSTER_NAME
from utils.s3 import generate_presigned_url


VERSION_REGEX_STR = r"\d+\.\d+\.\d+"

FIRMWARE_FILE_REGEX = re.compile(rf"^{VERSION_REGEX_STR}\.bin$")

SOFTWARE_INSTALLER_PREFIX = "software/MantarrayController-Setup-prod"
SOFTWARE_INSTALLER_VERSION_REGEX = re.compile(rf"{SOFTWARE_INSTALLER_PREFIX}-({VERSION_REGEX_STR})\.exe")


def create_dependency_mapping():
    """Create dependency mappings of SW/FW/HW versions as a dict.

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
            key for item in firmware_file_objs["Contents"] if FIRMWARE_FILE_REGEX.search(key := item["Key"])
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
    cfw_to_hw = {cfw: VersionInfo.parse(hw) for cfw, hw in cfw_to_hw.items()}
    try:
        cfw_version = sorted(cfw for cfw, hw in cfw_to_hw.items() if hw == device_hw_version)[-1]
    except IndexError:
        cfw_version = sorted(cfw for cfw, hw in cfw_to_hw.items() if device_hw_version < hw)[0]
    return cfw_version


def resolve_versions(hardware_version):
    cfw_to_hw, cfw_to_mfw, mfw_to_sw = create_dependency_mapping()
    cfw = get_cfw_from_hw(cfw_to_hw, hardware_version)
    mfw = cfw_to_mfw[cfw]
    sw = mfw_to_sw[mfw]
    return {"sw": sw, "main-fw": mfw, "channel-fw": cfw}


def get_download_url(version, firmware_type):
    bucket = f"{CLUSTER_NAME}-{firmware_type}-firmware"
    file_name = f"{version}.bin"
    url = generate_presigned_url(bucket=bucket, key=file_name)
    return url


def get_previous_software_version(sw_version):
    s3_client = boto3.client("s3")

    # Tanner (10/18/22): this will always error in test cluster since this bucket does not exist
    bucket = "downloads.curibio.com"

    sw_installer_objs = s3_client.list_objects(Bucket=bucket, Prefix=SOFTWARE_INSTALLER_PREFIX)
    sw_installer_names = [item["Key"] for item in sw_installer_objs["Contents"]]
    sw_versions = [
        regex_res[0]
        for name in sw_installer_names
        if (regex_res := SOFTWARE_INSTALLER_VERSION_REGEX.findall(name))
    ]

    sw_version_info = VersionInfo.parse(sw_version)
    try:
        previous_sw_version = sorted(v for v in sw_versions if v < sw_version_info)[-1]
    except IndexError:
        previous_sw_version = None

    return previous_sw_version


def get_required_sw_version_range(main_fw_version):
    *_, mfw_to_sw = create_dependency_mapping()

    min_sw_version = mfw_to_sw[main_fw_version]

    main_fw_version_info = VersionInfo.parse(main_fw_version)
    try:
        next_main_fw_version = sorted(v for v in mfw_to_sw if v > main_fw_version_info)[0]
    except IndexError:
        max_sw_version = None
    else:
        sw_version_upper_bound = mfw_to_sw[next_main_fw_version]
        max_sw_version = get_previous_software_version(sw_version_upper_bound)

    return {"min_sw": min_sw_version, "max_sw": max_sw_version}
