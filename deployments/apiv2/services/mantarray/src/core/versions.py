import functools
import re

import boto3
from semver import VersionInfo

from .config import CLUSTER_NAME
from utils.s3 import generate_presigned_url


DOWNLOADS_BUCKET_NAME = "downloads.curibio.com" if CLUSTER_NAME == "prod" else "downloads.curibio-test.com"

VERSION_REGEX_STR = r"\d+\.\d+\.\d+"

FIRMWARE_FILE_REGEX = re.compile(rf"^{VERSION_REGEX_STR}\.bin$")

SOFTWARE_INSTALLER_PREFIX = "software/MantarrayController-Setup-prod"
SOFTWARE_INSTALLER_VERSION_REGEX = re.compile(rf"{SOFTWARE_INSTALLER_PREFIX}-({VERSION_REGEX_STR})\.exe$")


class NoPreviousSoftwareVersionError(Exception):
    pass


def filter_and_sort_semvers(version_container, filter_fn=None, return_keys=False):
    if filter_fn is None:

        def no_filter(*_):
            return True

        filter_fn = no_filter

    def filter_fn_adj(*args):
        return filter_fn(*[VersionInfo.parse(arg) for arg in args])

    if isinstance(version_container, dict):
        filtered = [(k if return_keys else v) for k, v in version_container.items() if filter_fn_adj(k, v)]
    else:
        if return_keys:
            raise ValueError("Cannot use return_keys if version_container is not a dict")
        filtered = [v for v in version_container if filter_fn_adj(v)]

    return sorted(filtered, key=VersionInfo.parse)


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
    fass_partial = functools.partial(filter_and_sort_semvers, cfw_to_hw, return_keys=True)
    try:
        return fass_partial(lambda _, hw: hw == device_hw_version)[-1]
    except IndexError:
        # if this point reached, then the given HW version is not directly referenced by any channel FW
        # files in S3, so assume that the lowest channel FW version to point to a greater HW version
        # is the correct channel FW version
        # Tanner (10/19/22): in practice, this should never happen since a HW update will always
        # require a channel FW update
        return fass_partial(lambda _, hw: hw > device_hw_version)[0]


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


def get_all_sw_versions():
    s3_client = boto3.client("s3")

    all_sw_installer_objs = s3_client.list_objects(
        Bucket=DOWNLOADS_BUCKET_NAME, Prefix=SOFTWARE_INSTALLER_PREFIX
    )
    all_sw_installer_names = [item["Key"] for item in all_sw_installer_objs["Contents"]]

    all_sw_versions = [
        regex_res[0]
        for name in all_sw_installer_names
        if (regex_res := SOFTWARE_INSTALLER_VERSION_REGEX.findall(name))
    ]
    return all_sw_versions


def get_previous_software_version(all_sw_versions, current_sw_version):
    try:
        return filter_and_sort_semvers(all_sw_versions, lambda sw: sw < current_sw_version)[-1]
    except IndexError:
        raise NoPreviousSoftwareVersionError()


def get_latest_software_version(all_sw_versions):
    return filter_and_sort_semvers(all_sw_versions)[-1]


def get_required_sw_version_range(main_fw_version):
    *_, mfw_to_sw = create_dependency_mapping()

    min_sw_version = mfw_to_sw[main_fw_version]

    all_sw_versions = get_all_sw_versions()

    try:
        next_min_sw_version = filter_and_sort_semvers(
            set(mfw_to_sw.values()), lambda sw: sw > min_sw_version
        )[0]
    except IndexError:
        # if this point is reached, then the given main FW version is the latest version,
        # and thus currently does not have a defined upper bound of compatiblity,
        # so set to a very high number that will never be reached
        max_sw_version = get_latest_software_version(all_sw_versions)
    else:
        max_sw_version = get_previous_software_version(all_sw_versions, next_min_sw_version)

    return {"min_sw": min_sw_version, "max_sw": max_sw_version}
