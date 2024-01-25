import semver

from .config import CLUSTER_NAME
from utils.s3 import generate_presigned_url


class NoPreviousSoftwareVersionError(Exception):
    pass


class NoCompatibleVersionsError(Exception):
    pass


def get_fw_download_url(version, firmware_type):
    bucket = f"{CLUSTER_NAME}-{firmware_type}-firmware"
    file_name = f"{version}.bin"
    url = generate_presigned_url(bucket=bucket, key=file_name)
    return url


def get_latest_compatible_versions(all_compatible_versions: list[dict[str, str]]):
    if not all_compatible_versions:
        raise NoCompatibleVersionsError()

    labelled_items = {versions["channel_fw_version"]: versions for versions in all_compatible_versions}
    highest_cfw = _filter_and_sort_semvers(labelled_items.keys())[-1]
    return labelled_items[highest_cfw]


def get_required_sw_version_range(
    main_fw_version: str,
    main_fw_compatibility: list[dict[str, str]],
    ma_sw_versions: list[dict[str, str]],
    sting_sw_versions: list[dict[str, str]],
    remove_internal: bool,
):
    mfw_to_ma_sw = {d["main_fw_version"]: d["min_ma_controller_version"] for d in main_fw_compatibility}
    mfw_to_sting_sw = {d["main_fw_version"]: d["min_sting_controller_version"] for d in main_fw_compatibility}

    ma_sw_version_state = {d["version"]: d["state"] for d in ma_sw_versions}
    sting_sw_version_state = {d["version"]: d["state"] for d in sting_sw_versions}

    version_bounds = {}
    for sw_type, fw_mapping, sw_version_state in [
        ("sw", mfw_to_ma_sw, ma_sw_version_state),
        ("sting_sw", mfw_to_sting_sw, sting_sw_version_state),
    ]:
        min_sw_version_for_fw = fw_mapping[main_fw_version]
        min_sw_versions = _filter_and_sort_semvers(fw_mapping.values())

        # TODO add 'state' column to SW versions and filter them accordingly
        all_sw_versions = _filter_and_sort_semvers(
            sw_version_state.keys(), lambda sw: not remove_internal or sw_version_state[str(sw)] == "external"
        )

        try:
            min_sw_version_of_next_main_fw = _filter_and_sort_semvers(
                min_sw_versions, lambda sw: sw > min_sw_version_for_fw
            )[0]
        except IndexError:
            # given main FW version is the latest version and thus the max SW version should be the current max SW version released on prod
            max_sw_version_for_fw = all_sw_versions[-1]
        else:
            # there exists a subsequent main FW version and the max SW version should be whichever SW version immediately precedes the min version tied to this subsequent FW version
            max_sw_version_for_fw = _get_previous_sw_version(all_sw_versions, min_sw_version_of_next_main_fw)

        version_bounds.update(
            {f"min_{sw_type}": f"{min_sw_version_for_fw}-pre.0", f"max_{sw_type}": f"{max_sw_version_for_fw}"}
        )

    return version_bounds


# HELPERS


def _filter_and_sort_semvers(version_container, filter_fn=None, return_keys=False):
    if filter_fn is None:

        def no_filter(*_):
            return True

        filter_fn = no_filter

    def filter_fn_adj(*args):
        return filter_fn(*[semver.Version.parse(arg) for arg in args])

    if isinstance(version_container, dict):
        filtered = [(k if return_keys else v) for k, v in version_container.items() if filter_fn_adj(k, v)]
    else:
        if return_keys:
            raise ValueError("Cannot use return_keys if version_container is not a dict")
        filtered = [v for v in version_container if filter_fn_adj(v)]

    return sorted(filtered, key=semver.Version.parse)


def _get_previous_sw_version(all_sw_versions, current_sw_version):
    try:
        return _filter_and_sort_semvers(all_sw_versions, lambda sw: sw < current_sw_version)[-1]
    except IndexError:
        # TODO when could this happen?
        raise NoPreviousSoftwareVersionError()
