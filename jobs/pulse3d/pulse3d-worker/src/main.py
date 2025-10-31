import asyncio
from dataclasses import asdict
import json
import os
import tempfile
from typing import Any
from zipfile import ZipFile

import asyncpg
import boto3
import polars as pl
import structlog
from jobs import EmptyQueue, get_item
from mantarray_magnet_finding.exceptions import UnableToConvergeError
from curibio_analysis_lib import NormalizationMethods, FullPlatemap
from pulse3D import metrics
from pulse3D import peak_finding as peak_finder
from pulse3D import rendering as renderer
from pulse3D.constants import PACKAGE_VERSION as PULSE3D_VERSION
from pulse3D.data_loader import from_s3, InstrumentTypes
from pulse3D.data_loader.utils import get_metadata_cls
from pulse3D.peak_finding import LoadedDataWithFeatures
from pulse3D.pre_analysis import (
    PreProcessedData,
    pre_process,
    process,
    post_process,
    sort_wells_in_df,
    apply_window_to_df,
)
from pulse3D.rendering import OutputFormats
from structlog.contextvars import bind_contextvars, clear_contextvars, merge_contextvars
from utils.s3 import upload_file_to_s3

from lib.db import PULSE3D_UPLOADS_BUCKET, insert_metadata_into_pg
from lib.queries import SELECT_UPLOAD_DETAILS

structlog.configure(
    processors=[
        merge_contextvars,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M.%S"),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]
)

s3_client = boto3.client("s3")

logger = structlog.get_logger()


# TODO could use a better data structure for this
def _create_file_info(base_dir: str, upload_prefix: str, job_id: str) -> dict[str, Any]:
    pre_process_dir = os.path.join(base_dir, "pre-process")
    os.mkdir(pre_process_dir)
    pre_process_filename = "pre-process.zip"
    pre_process_file_s3_key = f"{upload_prefix}/pre-process/{PULSE3D_VERSION}/{pre_process_filename}"
    pre_process_file_path = os.path.join(pre_process_dir, pre_process_filename)

    pre_analysis_dir = os.path.join(base_dir, "pre-analysis")
    os.mkdir(pre_analysis_dir)
    pre_analysis_filename = "pre-analysis.zip"
    pre_analysis_file_s3_key = f"{upload_prefix}/{job_id}/{pre_analysis_filename}"
    pre_analysis_file_path = os.path.join(pre_analysis_dir, pre_analysis_filename)

    peak_finding_dir = os.path.join(base_dir, "peak_finding")
    os.mkdir(peak_finding_dir)
    peak_finding_filename = "peaks_valleys.parquet"
    peak_finding_s3_key = f"{upload_prefix}/{job_id}/{peak_finding_filename}"
    peak_finding_file_path = os.path.join(base_dir, peak_finding_filename)

    metrics_dir = os.path.join(base_dir, "metrics")
    os.mkdir(metrics_dir)
    per_twitch_metrics_filename = "per_twitch_metrics.parquet"
    per_twitch_metrics_s3_key = f"{upload_prefix}/{job_id}/{per_twitch_metrics_filename}"
    per_twitch_metrics_file_path = os.path.join(base_dir, per_twitch_metrics_filename)
    aggregate_metrics_filename = "aggregate_metrics.parquet"
    aggregate_metrics_s3_key = f"{upload_prefix}/{job_id}/{aggregate_metrics_filename}"
    aggregate_metrics_file_path = os.path.join(base_dir, aggregate_metrics_filename)

    return {
        "zip_contents": {
            "tissue": "tissue_waveforms.parquet",
            "stim": "stim_waveforms.parquet",
            "background": "background.parquet",
            "metadata": "metadata.json",
        },
        "pre_process": {
            "dir": pre_process_dir,
            "filename": pre_process_filename,
            "file_path": pre_process_file_path,
            "s3_key": pre_process_file_s3_key,
        },
        "pre_analysis": {
            "dir": pre_analysis_dir,
            "filename": pre_analysis_filename,
            "file_path": pre_analysis_file_path,
            "s3_key": pre_analysis_file_s3_key,
        },
        "peak_finding": {
            "dir": peak_finding_dir,
            "filename": peak_finding_filename,
            "file_path": peak_finding_file_path,
            "s3_key": peak_finding_s3_key,
        },
        "per_twitch_metrics": {
            "dir": metrics_dir,
            "filename": per_twitch_metrics_filename,
            "file_path": per_twitch_metrics_file_path,
            "s3_key": per_twitch_metrics_s3_key,
        },
        "aggregate_metrics": {
            "dir": metrics_dir,
            "filename": aggregate_metrics_filename,
            "file_path": aggregate_metrics_file_path,
            "s3_key": aggregate_metrics_s3_key,
        },
    }


def _upload_pre_zip(data_container, file_info, pre_step_name) -> None:
    try:
        logger.info(f"Uploading {pre_step_name} data to S3")
        zipfile_path = file_info[pre_step_name]["file_path"]
        with ZipFile(zipfile_path, "w") as z:
            for zip_key, container_key in [
                ("tissue", "tissue_waveforms"),
                ("stim", "stim_waveforms"),
                ("background", "background_data"),
            ]:
                df = getattr(data_container, container_key)
                if df is None:  # stim and background can be None
                    continue

                file_path = os.path.join(file_info[pre_step_name]["dir"], file_info["zip_contents"][zip_key])
                df.write_parquet(file_path)
                z.write(file_path, file_info["zip_contents"][zip_key])

            metadata_path = os.path.join(
                file_info[pre_step_name]["dir"], file_info["zip_contents"]["metadata"]
            )
            with open(metadata_path, "w") as f:
                f.write(data_container.metadata.model_dump_json())
            z.write(metadata_path, "metadata.json")

        s3_key = file_info[pre_step_name]["s3_key"]
        upload_file_to_s3(bucket=PULSE3D_UPLOADS_BUCKET, key=s3_key, file=zipfile_path)
        logger.info(f"Uploaded {pre_step_name} data to S3 under key: {s3_key}")
    except Exception:
        logger.exception(f"Upload of {pre_step_name} data to S3 failed")
        raise


@get_item(queue=f"pulse3d-v{PULSE3D_VERSION}")
async def process_item(con, item):
    # keeping initial log without bound variables
    logger.info(f"Processing item: {item}")

    job_metadata = {"processed_by": PULSE3D_VERSION}
    outfile_key = None

    # Tanner (3/27/24): this is specifically for human-readable error messages. The actual message in the exception is handled separately
    error_msg = None

    try:
        try:
            job_id = item["id"]
            upload_id = item["upload_id"]
            upload_details = await con.fetchrow(SELECT_UPLOAD_DETAILS, upload_id)

            re_analysis = False
            interactive_analysis = False

            # bind details to logger
            bind_contextvars(
                upload_id=str(upload_id),
                job_id=str(job_id),
                customer_id=str(upload_details["customer_id"]),
                user_id=str(upload_details["user_id"]),
            )

            logger.info("Starting job")

            prefix = upload_details["prefix"]
            metadata = json.loads(item["meta"])
            upload_filename = upload_details["filename"]
        except Exception:
            logger.exception("Fetching upload details failed")
            raise

        # remove params that were not given as these already have default values
        analysis_params = {k: v for k, v in metadata["analysis_params"].items() if v is not None}

        # pre-processing params, if any of these are set then pre-processing must be re-ran
        pre_processing_params = {
            k: v for k in ["high_fidelity_magnet_processing"] if (v := analysis_params.get(k)) is not None
        }
        # need to rename this param
        if v := pre_processing_params.pop("high_fidelity_magnet_processing", None):
            pre_processing_params["compute_constrained_estimations"] = v

        pre_analysis_params = {
            k: v
            for k, v in analysis_params.items()
            if k in ["stiffness_factor", "detrend", "disable_background_subtraction"]
        }
        # need to rename these params
        if post_stiffness_factor := pre_analysis_params.pop("stiffness_factor", None):
            pre_analysis_params["post_stiffness_factor"] = post_stiffness_factor
        if disable_bg_sub := pre_analysis_params.pop("disable_background_subtraction", None):
            pre_analysis_params["undo_background_subtraction"] = disable_bg_sub

        post_process_params = {
            k: v
            for k, v in analysis_params.items()
            if k in ["normalization_method", "start_time", "end_time"]
        }

        with tempfile.TemporaryDirectory(dir="/tmp") as tmpdir:
            file_info = _create_file_info(tmpdir, prefix, str(job_id))

            # download existing peak finding data
            try:
                # attempt to download existing peak finding data from s3, will only exist for interactive analysis jobs
                s3_client.download_file(
                    PULSE3D_UPLOADS_BUCKET,
                    file_info["peak_finding"]["s3_key"],
                    file_info["peak_finding"]["file_path"],
                )
                interactive_analysis = True
                logger.info(f"Downloaded peaks and valleys to {file_info['peak_finding']['file_path']}")
            except Exception:  # TODO catch only boto3 errors here?
                logger.info("No existing peaks and valleys found for recording")

            pre_processed_data = None

            # download existing pre-process data
            try:
                s3_client.download_file(
                    PULSE3D_UPLOADS_BUCKET,
                    file_info["pre_process"]["s3_key"],
                    file_info["pre_process"]["file_path"],
                )
                logger.info(
                    f"Downloaded existing pre-process data to {file_info['pre_process']['file_path']}"
                )
            except Exception:
                logger.info(f"No existing pre-process data found for recording {upload_filename}")
            else:
                try:
                    with ZipFile(file_info["pre_process"]["file_path"]) as z:
                        z.extractall(file_info["pre_process"]["dir"])

                    pre_process_tissue_waveforms = pl.read_parquet(
                        os.path.join(file_info["pre_process"]["dir"], file_info["zip_contents"]["tissue"])
                    )

                    pre_process_stim_waveforms_path = os.path.join(
                        file_info["pre_process"]["dir"], file_info["zip_contents"]["stim"]
                    )
                    pre_process_stim_waveforms = None
                    if os.path.exists(pre_process_stim_waveforms_path):
                        pre_process_stim_waveforms = pl.read_parquet(pre_process_stim_waveforms_path)

                    pre_process_background_data_path = os.path.join(
                        file_info["pre_process"]["dir"], file_info["zip_contents"]["background"]
                    )
                    pre_process_background_data = None
                    if os.path.exists(pre_process_background_data_path):
                        pre_process_background_data = pl.read_parquet(pre_process_background_data_path)

                    pre_process_metadata_dict = json.load(
                        open(
                            os.path.join(
                                file_info["pre_process"]["dir"], file_info["zip_contents"]["metadata"]
                            )
                        )
                    )
                    pre_process_metadata = get_metadata_cls(pre_process_metadata_dict)

                    pre_processed_data = PreProcessedData(
                        tissue_waveforms=pre_process_tissue_waveforms,
                        stim_waveforms=pre_process_stim_waveforms,
                        background_data=pre_process_background_data,
                        metadata=pre_process_metadata,
                    )

                    re_analysis = True
                except Exception:
                    logger.exception("Error loading existing pre-process data")

            if pre_processing_params or not re_analysis:
                try:
                    logger.info("Starting DataLoader")
                    key = f"{prefix}/{upload_filename}"
                    loaded_data = from_s3(PULSE3D_UPLOADS_BUCKET, key)
                except Exception:
                    logger.exception("DataLoader failed")
                    error_msg = "Loading recording data failed"
                    raise

                try:
                    logger.info("Starting Pre-Analysis pre-processing")
                    pre_processed_data = pre_process(loaded_data, **pre_processing_params)
                except UnableToConvergeError:
                    error_msg = "Unable to converge, low quality calibration data"
                    logger.exception(error_msg)
                    raise
                except Exception:
                    error_msg = "Pre-Analysis failed (1)"
                    logger.exception("Pre-Analysis pre-processing failed")
                    raise

                # upload pre-processed data if using default pre-processing params
                if not pre_processing_params:
                    _upload_pre_zip(pre_processed_data, file_info, "pre_process")

            if pre_processed_data is None:
                raise Exception("Something went wrong, pre-processed data was never set")

            try:
                logger.info("Starting Pre-Analysis")
                pre_analyzed_data = process(pre_processed_data, **pre_analysis_params)
            except Exception:
                error_msg = "Pre-Analysis failed (2)"
                logger.exception("Pre-Analysis failed")
                raise

            # upload pre-analysis data
            _upload_pre_zip(pre_analyzed_data, file_info, "pre_analysis")

            try:
                logger.info("Starting Pre-Analysis post-processing")
                # mantarray always uses the same normalization
                if pre_analyzed_data.metadata.instrument_type == InstrumentTypes.MANTARRAY:
                    post_process_params["normalization_method"] = NormalizationMethods.F_SUB_FMIN

                analyzable_data = post_process(pre_analyzed_data, **post_process_params)
            except Exception:
                error_msg = "Pre-Analysis failed (3)"
                logger.exception("Pre-Analysis post-processing failed")
                raise

            if interactive_analysis:
                logger.info("Loading IA data")
                try:
                    features_df = pl.read_parquet(file_info["peak_finding"]["file_path"])

                    features_df = sort_wells_in_df(features_df, analyzable_data.metadata.total_well_count)
                    features_df = apply_window_to_df(
                        features_df, df_name_to_log="features", **post_process_params
                    )

                    data_with_features = LoadedDataWithFeatures(
                        **asdict(analyzable_data), tissue_features=features_df
                    )

                    logger.info("Loaded data from IA")
                except Exception:
                    error_msg = "Loading interactive analysis data failed"
                    logger.exception("Loading IA data failed")
                    raise
            else:
                try:
                    logger.info("Running PeakDetector")
                    peak_detector_args = {
                        param: val
                        for param in (
                            "relative_prominence_factor",
                            "noise_prominence_factor",
                            "height_factor",
                            "width_factors",
                            "max_frequency",
                            "valley_search_duration",
                            "upslope_duration",
                            "upslope_noise_allowance_duration",
                        )
                        if (val := analysis_params.get(param)) is not None
                    }
                    data_with_features = peak_finder.run(analyzable_data, alg_args=peak_detector_args)
                except Exception:
                    error_msg = "Peak detection failed"
                    logger.exception("PeakDetector failed")
                    raise

            # Windowing is applied here in the worker, not by IA (just sets the bounds), so always upload the parquet file in case a change is made here
            logger.info("Uploading peak detection results")
            try:
                data_with_features.tissue_features.write_parquet(file_info["peak_finding"]["file_path"])
                upload_file_to_s3(
                    bucket=PULSE3D_UPLOADS_BUCKET,
                    key=file_info["peak_finding"]["s3_key"],
                    file=file_info["peak_finding"]["file_path"],
                )
                logger.info(
                    f"Uploaded peak detection results to {PULSE3D_UPLOADS_BUCKET}/{file_info['peak_finding']['s3_key']}"
                )
            except Exception:
                logger.exception("Upload of peak detection results failed")
                raise

            try:
                logger.info("Creating metrics")
                metrics_args = {
                    arg_name: val
                    for arg_name, orig_name in (
                        ("widths", "twitch_widths"),
                        ("relaxation_search_limit_secs", "relaxation_search_limit_secs"),
                    )
                    if (val := analysis_params.get(orig_name)) is not None
                }
                if well_groups := analysis_params.get("well_groups"):
                    metrics_args["platemap_override"] = FullPlatemap.from_abbreviated(
                        well_groups, analysis_params.get("platemap_name")
                    )

                metrics_output = metrics.run(data_with_features, **metrics_args)
                logger.info("Created metrics")
            except Exception:
                error_msg = "Metric creation failed"
                logger.exception("Metrics failed")
                raise

            # Upload metrics
            logger.info("Uploading per-twitch metrics")
            try:
                metrics_output.per_twitch_metrics.write_parquet(file_info["per_twitch_metrics"]["file_path"])
                upload_file_to_s3(
                    bucket=PULSE3D_UPLOADS_BUCKET,
                    key=file_info["per_twitch_metrics"]["s3_key"],
                    file=file_info["per_twitch_metrics"]["file_path"],
                )
                logger.info(
                    f"Uploaded per-twitch metrics to {PULSE3D_UPLOADS_BUCKET}/{file_info['per_twitch_metrics']['s3_key']}"
                )
            except Exception:
                logger.exception("Upload of per-twitch metrics failed")
                raise
            logger.info("Uploading aggregate metrics")
            try:
                metrics_output.aggregate_metrics.write_parquet(file_info["aggregate_metrics"]["file_path"])
                upload_file_to_s3(
                    bucket=PULSE3D_UPLOADS_BUCKET,
                    key=file_info["aggregate_metrics"]["s3_key"],
                    file=file_info["aggregate_metrics"]["file_path"],
                )
                logger.info(
                    f"Uploaded aggregate metrics to {PULSE3D_UPLOADS_BUCKET}/{file_info['aggregate_metrics']['s3_key']}"
                )
            except Exception:
                logger.exception("Upload of aggregate metrics failed")
                raise

            try:
                logger.info("Running renderer")

                renderer_args = {
                    arg_name: val
                    for arg_name in (
                        "include_stim_protocols",
                        "stim_waveform_format",
                        "data_type",
                        "normalize_y_axis",
                        "max_y",
                    )
                    if (val := analysis_params.get(arg_name)) is not None
                }
                # if a new name has been given in the upload form, then replace here, else use original name
                if name_override := metadata.get("name_override"):
                    renderer_args["output_file_name"] = name_override

                if data_type_override := renderer_args.get("data_type"):
                    renderer_args["data_type"] = data_type_override.lower()

                # nautilai's processing handles normalization differently than mantarray's
                if metrics_output.metadata.instrument_type == InstrumentTypes.NAUTILAI:
                    renderer_args["normalize_y_axis"] = False

                renderer_args["custom_analysis_params"] = {
                    arg_name: val
                    for arg_name, val in analysis_params.items()
                    if val is not None and arg_name
                    # all these values already have a home on the metadata sheet
                    not in (
                        "start_time",
                        "end_time",
                        "stiffness_factor",
                        "data_type",
                        "platemap_name",
                        "well_groups",
                    )
                }

                renderer_args["output_dir"] = tmpdir

                output_filename = renderer.run(
                    metrics_output, OutputFormats.XLSX, output_format_args=renderer_args
                )
                logger.info("Renderer complete")
            except Exception:
                error_msg = "Output file creation failed"
                logger.exception("Renderer failed")
                raise

            try:
                logger.info("Uploading renderer output")
                outfile_prefix = prefix.replace("uploads/", "analyzed/")
                outfile_key = f"{outfile_prefix}/{job_id}/{output_filename}"
                upload_file_to_s3(
                    bucket=PULSE3D_UPLOADS_BUCKET, key=outfile_key, file=os.path.join(tmpdir, output_filename)
                )
                logger.info(f"Uploaded {output_filename} to {PULSE3D_UPLOADS_BUCKET}/{outfile_key}")
            except Exception:
                logger.exception("Upload of renderer output failed")
                raise

            try:
                upload_meta = json.loads(upload_details["meta"])

                # letting pydantic convert to JSON will handle serialization of all data types, so do that and then load into a dict
                pre_process_meta_res = json.loads(pre_processed_data.metadata.model_dump_json())
                new_meta = {
                    k: pre_process_meta_res[k] for k in (pre_process_meta_res.keys() - upload_meta.keys())
                }
                if new_meta:
                    logger.info(f"Adding metadata to upload in DB: {new_meta}")
                    upload_meta |= new_meta
                    await con.execute(
                        "UPDATE uploads SET meta=$1 WHERE id=$2", json.dumps(upload_meta), upload_id
                    )
                else:
                    logger.info("No upload metadata to update in DB")
            except Exception:
                # Tanner (7/29/24): don't raise the exception, no reason this should cause the whole analysis to fail
                logger.exception("Updating metadata of upload in DB failed")

            try:
                await insert_metadata_into_pg(
                    con,
                    pre_processed_data.metadata,
                    upload_details["customer_id"],
                    upload_details["user_id"],
                    upload_id,
                    outfile_key,
                    re_analysis,
                )

                if data_type_override := analysis_params.get("data_type"):
                    data_type = data_type_override
                else:
                    data_type = pre_analyzed_data.metadata.data_type

                job_metadata |= {
                    "plate_barcode": pre_analyzed_data.metadata.plate_barcode,
                    "recording_length_ms": pre_analyzed_data.metadata.full_recording_length,
                    "data_type": data_type,
                }
                if pre_analyzed_data.metadata.instrument_type == InstrumentTypes.MANTARRAY:
                    job_metadata["stim_barcode"] = pre_analyzed_data.metadata.stim_barcode

            except Exception:
                logger.exception("Failed to insert metadata to db")
                raise

    except Exception as e:
        job_metadata["error"] = repr(e)
        result = "error"
        # some errors do not include an error message
        if error_msg:
            job_metadata["error_msg"] = error_msg
    else:
        logger.info("Job complete")
        result = "finished"

    # clear bound variables (IDs) for this job to reset for next job
    clear_contextvars()

    return result, job_metadata, outfile_key


async def main():
    try:
        logger.info(f"Pulse3D Worker v{PULSE3D_VERSION} started")

        with tempfile.TemporaryDirectory(dir="/tmp") as tmpdir:
            # get barcode config from s3
            barcode_config_s3_key = "config/barcode.json"
            barcode_config_dir = os.path.join(tmpdir, "config")
            barcode_config_path = os.path.join(barcode_config_dir, "barcode.json")
            logger.info(
                f"Downloading barcode config file from S3 (key: '{barcode_config_s3_key}') to '{barcode_config_path}'"
            )
            try:
                os.mkdir(barcode_config_dir)
                s3_client.download_file(PULSE3D_UPLOADS_BUCKET, barcode_config_s3_key, barcode_config_path)
            except Exception:
                logger.exception("Failed to download barcode config file from S3")
            else:
                os.environ["P3D_BARCODE_CONFIG_PATH"] = barcode_config_path

            # process jobs
            DB_PASS = os.getenv("POSTGRES_PASSWORD")
            DB_USER = os.getenv("POSTGRES_USER", default="curibio_jobs")
            DB_HOST = os.getenv("POSTGRES_SERVER", default="psql-rds.default")
            DB_NAME = os.getenv("POSTGRES_DB", default="curibio")

            dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
            async with asyncpg.create_pool(dsn=dsn) as pool:
                async with pool.acquire() as con, pool.acquire() as con_to_update_job_result:
                    while True:
                        try:
                            logger.info("Pulling job from queue")
                            await process_item(con=con, con_to_update_job_result=con_to_update_job_result)
                        except EmptyQueue as e:
                            logger.info(f"No jobs in queue: {e}")
                            return
                        except Exception:
                            logger.exception("Processing queue item failed")
                            return
    finally:
        os.environ.pop("P3D_BARCODE_CONFIG_PATH", None)
        logger.info(f"Pulse3D Worker v{PULSE3D_VERSION} terminating")


if __name__ == "__main__":
    asyncio.run(main())
