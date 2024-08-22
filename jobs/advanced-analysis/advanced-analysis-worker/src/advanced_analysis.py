# -*- coding: utf-8 -*-
from dataclasses import dataclass
import datetime
from enum import auto
from enum import StrEnum
import json
import os
from typing import Any
from typing import TypeAlias

from immutabledict import immutabledict
import polars as pl
from xlsxwriter import Workbook

ADVANCED_ANALYSIS_VERSION = "0.1.0rc0"

# TODO add logging


@dataclass
class SingleAnalysisContainer:
    name: str
    agg_metrics: pl.DataFrame
    recording_metadata: dict[str, Any]
    p3d_analysis_metadata: dict[str, Any]
    platemap: dict[str, Any]


@dataclass
class CombinedContainer:
    combined_p3d_metadata: pl.DataFrame
    ungrouped_aggs: pl.DataFrame
    group_aggs: pl.DataFrame
    advanced_analysis_metadata: dict[str, Any]


# TODO The following could be shared with Pulse3D
###############

Number: TypeAlias = int | float

NOT_APPLICABLE_LABEL = "N/A"


def _get_meta_display_name(metadata_val: Any) -> Any:
    return str(metadata_val) if metadata_val not in ("", None) else NOT_APPLICABLE_LABEL


class MetadataDisplayNames(StrEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[str]) -> str:
        return name.replace("_", " ").title()

    # TODO include data type and normalization method for nautilai?
    filename = auto()
    file_type = auto()
    file_format_version = auto()
    plate_barcode = auto()
    stim_barcode = "Stimulation Lid Barcode"
    utc_beginning_recording = "UTC Timestamp of Beginning of Recording"
    post_stiffness_label = "Post Stiffness Factor"
    platemap_name = auto()
    instrument_serial_number = auto()
    software_release_version = auto()
    main_firmware_version = "Instrument Firmware Version"
    pulse3D_version = auto()
    file_creation_timestamp = auto()
    window_type = "Analysis Type (Full or Windowed)"
    window_start = "Analysis Start Time (seconds)"
    window_end = "Analysis End Time (seconds)"
    local_tz_beginning_recording = "Local Timestamp of Beginning of Recording"
    day = auto()


class DataTypes(StrEnum):
    FORCE = auto()
    CALCIUM = auto()
    VOLTAGE = auto()


class NormalizationMethods(StrEnum):
    F_SUB_FMIN = "F-Fmin"
    F_OVER_FMIN = "F/Fmin"
    DF_OVER_FMIN = "∆F/Fmin"


class TwitchMetrics(StrEnum):
    AMPLITUDE = auto()
    AUC = auto()
    CONTRACTION_TIME = "contraction_time_{width}"
    CONTRACTION_VELOCITY = "contraction_velocity"
    FRACTION_OF_MAX_AMPLITUDE = auto()
    FREQUENCY = auto()
    INTERVAL_IRREGULARITY = auto()
    PERIOD = auto()
    RELAXATION_TIME = "relaxation_time_{width}"
    RELAXATION_VELOCITY = "relaxation_velocity"
    WIDTH = "width_{width}"
    X_PEAK = auto()


_CALCULATED_METRIC_DISPLAY_NAMES: immutabledict[DataTypes, dict[TwitchMetrics, str]] = immutabledict(
    {
        DataTypes.FORCE: immutabledict(
            {
                TwitchMetrics.AMPLITUDE: "Active Twitch Force (μN)",
                TwitchMetrics.AUC: "Area Under Curve (μN * second)",
                TwitchMetrics.CONTRACTION_TIME: "Time From Contraction {width} to Peak (seconds)",
                TwitchMetrics.CONTRACTION_VELOCITY: "Twitch Contraction Velocity (μN/second)",
                TwitchMetrics.FRACTION_OF_MAX_AMPLITUDE: "Fraction of Maximum Active Twitch Force (μN)",
                TwitchMetrics.FREQUENCY: "Twitch Frequency (Hz)",
                TwitchMetrics.INTERVAL_IRREGULARITY: "Twitch Interval Irregularity (seconds)",
                TwitchMetrics.RELAXATION_TIME: "Time From Peak to Relaxation {width_inverse} (seconds)",
                TwitchMetrics.RELAXATION_VELOCITY: "Twitch Relaxation Velocity (μN/second)",
                TwitchMetrics.WIDTH: "Twitch Width {width} (seconds)",
                TwitchMetrics.PERIOD: "Twitch Period (seconds)",
                TwitchMetrics.X_PEAK: "Timepoint of Twitch Contraction (seconds)",
            }
        )
    }
    | {
        t: immutabledict(
            {
                TwitchMetrics.AMPLITUDE: "Fluorescence Transient Amplitude ({unit})",
                TwitchMetrics.AUC: "Area Under Fluorescence Transient (({unit}) * second)",
                TwitchMetrics.CONTRACTION_TIME: "Time From Rise {width} to Peak (seconds)",
                TwitchMetrics.CONTRACTION_VELOCITY: "Fluorescence Rise Rate (({unit})/second)",
                TwitchMetrics.FRACTION_OF_MAX_AMPLITUDE: "Fraction of Maximum Fluorescence Transient Amplitude",
                TwitchMetrics.FREQUENCY: "Fluorescence Transient Frequency (Hz)",
                TwitchMetrics.INTERVAL_IRREGULARITY: "Fluorescence Transient Period Irregularity (seconds)",
                TwitchMetrics.RELAXATION_TIME: "Time From Peak to Decay {width_inverse} (seconds)",
                TwitchMetrics.RELAXATION_VELOCITY: "Fluorescence Decay Rate (({unit})/second)",
                TwitchMetrics.WIDTH: "Fluorescence Transient Width {width} (seconds)",
                TwitchMetrics.PERIOD: "Fluorescence Transient Period (seconds)",
                TwitchMetrics.X_PEAK: "Timepoint of Peak Fluorescence Transient (seconds)",
            }
        )
        for t in (DataTypes.CALCIUM, DataTypes.VOLTAGE)
    }
)


def _get_metric_display_title(
    metric_name: TwitchMetrics,
    data_type: DataTypes,
    width: int | None = None,
    normalization_method: NormalizationMethods | None = None,
) -> str:
    format_kwargs: dict[str, Any] = {}
    if width is not None:
        format_kwargs |= {"width": width, "width_inverse": 100 - width}
    if normalization_method:
        format_kwargs["unit"] = normalization_method
    else:
        format_kwargs["unit"] = "au"

    display_title: str = _CALCULATED_METRIC_DISPLAY_NAMES[data_type][metric_name].format(**format_kwargs)
    return display_title


###############


# DATA LOADER


class NoDataLoadedError(Exception):
    pass


def load_from_dir(
    inputs_dir_path: str, sources_info: dict[str, dict[str, Any]]
) -> list[SingleAnalysisContainer]:
    input_containers = []
    for analysis_name in os.listdir(inputs_dir_path):
        with open(os.path.join(inputs_dir_path, analysis_name, "metadata.json")) as meta_file:
            recording_metadata = json.load(meta_file)
        agg_metrics = pl.read_parquet(
            os.path.join(inputs_dir_path, analysis_name, "aggregate_metrics.parquet")
        )
        source_info = sources_info[analysis_name]
        input_containers.append(
            SingleAnalysisContainer(
                name=analysis_name,
                agg_metrics=agg_metrics,
                recording_metadata=recording_metadata,
                p3d_analysis_metadata=source_info["p3d_analysis_metadata"],
                platemap=source_info["platemap"],
            )
        )

    if not input_containers:
        raise NoDataLoadedError()

    return input_containers


# LONGITUDINAL AGGREGATOR


class InconsistentP3dAnalysisParamsError(Exception):
    pass


def longitudinal_aggregator(containers, experiment_start_utc, local_tz_offset_hours):
    advanced_analysis_metadata = _get_advanced_analysis_metadata(containers)
    metadata_df = _create_p3d_metadata_df(containers, experiment_start_utc, local_tz_offset_hours)
    ungrouped_aggs = _create_ungrouped_aggs(containers)
    group_aggs = _create_group_aggs(ungrouped_aggs)
    return CombinedContainer(metadata_df, ungrouped_aggs, group_aggs, advanced_analysis_metadata)


# TODO should make a pydantic model or dataclass for the return type
def _get_advanced_analysis_metadata(containers: list[SingleAnalysisContainer]) -> dict[str, Any]:
    data_types = list({container.p3d_analysis_metadata["data_type"] for container in containers})
    if len(data_types) > 1:
        raise InconsistentP3dAnalysisParamsError(f"Multiple data types found: {data_types}")
    normalization_methods = list(
        {
            container.p3d_analysis_metadata["analysis_params"]["normalization_method"]
            for container in containers
        }
    )
    if len(normalization_methods) > 1:
        raise InconsistentP3dAnalysisParamsError(
            f"Multiple normalization methods found: {normalization_methods}"
        )

    normalization_method = normalization_methods[0]
    if normalization_method is not None:
        normalization_method = NormalizationMethods[normalization_method]

    return {"data_type": DataTypes[data_types[0].upper()], "normalization_method": normalization_method}


def _create_p3d_metadata_df(
    containers: list[SingleAnalysisContainer],
    experiment_start_utc: datetime.datetime,
    local_tz_offset_hours: Number,
) -> pl.DataFrame:
    combined_metadata_df = pl.DataFrame()

    for container in containers:
        # TODO potentially need to handle multiple datetime formats
        utc_beginning_recording = datetime.datetime.fromisoformat(
            container.recording_metadata["utc_beginning_recording"]
        )
        day = (utc_beginning_recording - experiment_start_utc).days
        p3d_analysis_meta = (
            container.recording_metadata
            | {
                "filename": container.p3d_analysis_metadata["filename"],
                "pulse3D_version": container.p3d_analysis_metadata["version"],
                "file_creation_timestamp": container.p3d_analysis_metadata["file_creation_timestamp"],
                "day": day,
                "local_tz_beginning_recording": utc_beginning_recording
                + datetime.timedelta(hours=local_tz_offset_hours),
                # this value is already in the stored metadata, but need to format it correctly
                "utc_beginning_recording": str(utc_beginning_recording),
            }
            | _get_window_info(
                container.p3d_analysis_metadata["analysis_params"],
                container.recording_metadata["full_recording_length"],
            )
        )
        p3d_analysis_meta = {
            display_name: _get_meta_display_name(p3d_analysis_meta[stored_name])
            for stored_name, display_name in MetadataDisplayNames.__members__.items()
        }
        metadata_df = pl.DataFrame(
            {
                "analysis_name": container.name,
                "key": p3d_analysis_meta.keys(),
                "val": p3d_analysis_meta.values(),
            }
        )
        combined_metadata_df = combined_metadata_df.vstack(metadata_df)

        # insert day back into metadata in container so it can be used later
        container.p3d_analysis_metadata["day"] = day

    return combined_metadata_df


def _create_ungrouped_aggs(containers: list[SingleAnalysisContainer]) -> pl.DataFrame:
    combined_df = pl.DataFrame()

    for container in containers:
        labels = container.platemap["labels"]
        formatted_labels = {well: label["name"] for label in labels for well in label["wells"]}
        formatted_agg = (
            container.agg_metrics.filter(pl.col("group").str.ends_with("_group").not_())
            .select(
                pl.col("group").alias("well"),
                pl.lit(container.name).alias("analysis_name"),
                "metric",
                "mean_twitches",
            )
            .join(
                pl.DataFrame(
                    {
                        "well": formatted_labels.keys(),
                        "group": formatted_labels.values(),
                        "day": container.p3d_analysis_metadata["day"],
                        "platemap_name": container.platemap["map_name"],
                    }
                ),
                on="well",
            )
        )
        combined_df = combined_df.vstack(formatted_agg)

    return combined_df


def _create_group_aggs(ungrouped_aggs: pl.DataFrame) -> pl.DataFrame:
    # TODO need to handle errors and edge cases. mean and std can both return None, std will raise a divide by zero error if there is only one sample
    return ungrouped_aggs.group_by("analysis_name", "group", "metric").agg(
        mean=pl.col("mean_twitches").mean(),
        std=pl.col("mean_twitches").std(),
        count=pl.col("group").count(),
        day=pl.col("day").first(),  # all days should be the same within the group, so grab the first value
    )


def _get_window_info(analysis_params: dict[str, Any], full_recording_length: Number) -> dict[str, Any]:
    full_recording_length = round(full_recording_length, 2)
    start_time = analysis_params["start_time"]
    if start_time is None:
        start_time = 0
    end_time = analysis_params["end_time"]
    if end_time is None:
        end_time = full_recording_length

    is_full_analysis = start_time == 0 and round(end_time, 2) == full_recording_length

    return {
        "window_start": start_time,
        "window_end": end_time,
        "window_type": "Full" if is_full_analysis else "Windowed",
    }


# RENDERER


def render(combined_container: CombinedContainer, output_name: str, output_dir: str | None = None) -> str:
    output_name += ".xlsx"
    if output_dir:
        output_path = os.path.join(output_dir, output_name)
    else:
        output_path = output_name

    workbook_options = {
        "nan_inf_to_errors": True,  # required so the NaN rows do not cause errors
        "strings_to_numbers": True,  # required so that numbers that are stored as strings will be converted to numbers in the xlsx sheet
    }
    with Workbook(output_path, workbook_options) as wb:
        _metadata_sheet(wb, combined_container.combined_p3d_metadata)
        _mean_sheet(wb, combined_container.group_aggs, combined_container.advanced_analysis_metadata)
        _ungrouped_sheet(wb, combined_container.ungrouped_aggs, combined_container.advanced_analysis_metadata)

    return output_name


def _metadata_sheet(wb: Workbook, metadata: pl.DataFrame) -> None:
    display_metadata = pl.DataFrame()

    # TODO try pivot here to clean this up
    for analysis_name in metadata["analysis_name"].unique():
        single_analysis_metadata = metadata.filter(pl.col("analysis_name") == analysis_name).select(
            "key", "val"
        )
        formatted_metadata = single_analysis_metadata.select("val").transpose(
            column_names=single_analysis_metadata["key"]
        )
        display_metadata = display_metadata.vstack(formatted_metadata)

    display_metadata = display_metadata.sort(MetadataDisplayNames.day, MetadataDisplayNames.filename)

    # TODO could make an enum for sheet names
    display_metadata.write_excel(wb, "Metadata")


def _mean_sheet(wb: Workbook, group_aggs: pl.DataFrame, advanced_analysis_metadata: dict[str, Any]) -> None:
    data_type = advanced_analysis_metadata["data_type"]
    normalization_method = advanced_analysis_metadata["normalization_method"]

    column = "group"
    values = ("mean", "std", "count")

    def rename_after_pivot(col: str) -> str:
        sep = f"_{column}_"
        if sep not in col:
            return col
        agg, group = col.split(sep)
        idx = values.index(agg) + 1
        return "_".join([group, str(idx), agg])

    formatted_group_aggs = group_aggs.pivot(values, index=["metric", "day"], columns=column)
    rename_map = {
        old: rename_after_pivot(old) for old in formatted_group_aggs.columns if old not in ("metric", "day")
    }
    formatted_group_aggs = (
        formatted_group_aggs.rename(rename_map)
        .select(
            pl.col("metric")
            .map_elements(
                lambda m: "Mean " + _create_metric_display_title(m, data_type, normalization_method)
            )
            .alias("Aggregate Metric"),
            pl.col("day").alias("Day"),
            *sorted(list(rename_map.values())),
        )
        .sort("Aggregate Metric", "Day")
    )

    formatted_group_aggs.write_excel(wb, "Mean")


def _ungrouped_sheet(
    wb: Workbook, ungrouped_aggs: pl.DataFrame, advanced_analysis_metadata: dict[str, Any]
) -> None:
    data_type = advanced_analysis_metadata["data_type"]
    normalization_method = advanced_analysis_metadata["normalization_method"]
    formatted_ungrouped_aggs = (
        ungrouped_aggs.with_columns(
            pl.concat_list("group", "platemap_name", "well").list.join("_").alias("pivot_col")
        )
        .pivot("mean_twitches", index=["metric", "day"], columns="pivot_col", sort_columns=True)
        .select(
            pl.col("metric")
            .map_elements(
                lambda m: "Mean " + _create_metric_display_title(m, data_type, normalization_method)
            )
            .alias("Aggregate Metric"),
            pl.col("day").alias("Day"),
            pl.exclude("metric", "day"),
        )
        .sort("Aggregate Metric", "Day")
    )

    formatted_ungrouped_aggs.write_excel(wb, "Ungrouped")


def _create_metric_display_title(
    metric_name: str, data_type: DataTypes, normalization_method: NormalizationMethods | None
) -> str:
    width = None

    metric_name_split = metric_name.split("_")
    if metric_name_split[-1].isdigit():
        *metric_name_split, width_str = metric_name_split
        width = int(width_str)
        if "relaxation" in metric_name:
            width = 100 - width
    metric_name = TwitchMetrics["_".join(metric_name_split).upper()]

    return _get_metric_display_title(metric_name, data_type, width, normalization_method)
