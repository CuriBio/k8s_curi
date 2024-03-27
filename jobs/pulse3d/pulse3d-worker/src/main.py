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
from pulse3D import metrics
from pulse3D import peak_finding as peak_finder
from pulse3D import rendering as renderer
from pulse3D.constants import PACKAGE_VERSION as PULSE3D_VERSION
from pulse3D.data_loader import from_file, InstrumentTypes
from pulse3D.data_loader.utils import get_metadata_cls
from pulse3D.data_loader.metadata import NormalizationMethods
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

    return {
        "zip_contents": {
            "tissue": "tissue_waveforms.parquet",
            "stim": "stim_waveforms.parquet",
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
    }


def _upload_pre_zip(data_container, file_info, pre_step_name) -> None:
    try:
        logger.info(f"Uploading {pre_step_name} data to S3")
        zipfile_path = file_info[pre_step_name]["file_path"]
        with ZipFile(zipfile_path, "w") as z:
            for data_type in ("tissue", "stim"):
                df = getattr(data_container, f"{data_type}_waveforms")
                if df is None:  # stim_waveforms can be None
                    continue

                file_path = os.path.join(
                    file_info[pre_step_name]["dir"], file_info["zip_contents"][data_type]
                )
                df.write_parquet(file_path)
                z.write(file_path, file_info["zip_contents"][data_type])

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

    s3_client = boto3.client("s3")
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
            # if a new name has been given in the upload form, then replace here, else use original name
            analysis_filename = (
                f"{name_override}.zip"
                if (name_override := metadata.get("name_override"))
                else upload_filename
            )
            analysis_name = os.path.splitext(analysis_filename)[0]
        except Exception:
            logger.exception("Fetching upload details failed")
            raise

        # remove params that were not given as these already have default values
        analysis_params = {k: v for k, v in metadata["analysis_params"].items() if v is not None}

        pre_analysis_params = {
            k: v for k, v in analysis_params.items() if k in ["stiffness_factor", "detrend"]
        }
        # need to rename this param
        if post_stiffness_factor := pre_analysis_params.pop("stiffness_factor", None):
            pre_analysis_params["post_stiffness_factor"] = post_stiffness_factor

        post_process_params = {
            k: v
            for k, v in analysis_params.items()
            if k in ["normalization_method", "start_time", "end_time"]
        }

        with tempfile.TemporaryDirectory(dir="/tmp") as tmpdir:
            file_info = _create_file_info(tmpdir, prefix, str(job_id))

            # download recording file
            try:
                key = f"{prefix}/{upload_filename}"
                recording_path = f"{tmpdir}/{analysis_filename}"
                s3_client.download_file(PULSE3D_UPLOADS_BUCKET, key, recording_path)
                logger.info(f"Downloaded recording file to {recording_path}")
            except Exception:
                logger.exception("Failed to download recording zip file")
                raise

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
                    pre_process_stim_waveforms = (
                        pl.read_parquet(pre_process_stim_waveforms_path)
                        if os.path.exists(pre_process_stim_waveforms_path)
                        else None
                    )

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
                        metadata=pre_process_metadata,
                    )

                    re_analysis = True
                except Exception:
                    logger.exception("Error loading existing pre-process data")

            if not re_analysis:
                try:
                    logger.info("Starting DataLoader")
                    loaded_data = from_file(recording_path)
                except Exception:
                    logger.exception("DataLoader failed")
                    error_msg = "Loading recording data failed"
                    raise

                try:
                    logger.info("Starting Pre-Analysis pre-processing")
                    pre_processed_data = pre_process(loaded_data)
                except UnableToConvergeError:
                    error_msg = "Unable to converge, low quality calibration data"
                    logger.exception(error_msg)
                    raise
                except Exception:
                    error_msg = "Pre-Analysis failed (1)"
                    logger.exception("Pre-Analysis pre-processing failed")
                    raise

                # upload pre-processed data
                _upload_pre_zip(pre_processed_data, file_info, "pre_process")

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
                        ("baseline_widths", "baseline_widths_to_use"),
                        ("well_groups", "well_groups"),
                    )
                    if (val := analysis_params.get(orig_name)) is not None
                }
                metrics_output = metrics.run(data_with_features, **metrics_args)
                logger.info("Created metrics")
            except Exception:
                error_msg = "Metric creation failed"
                logger.exception("Metrics failed")
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
                renderer_args["output_file_name"] = analysis_name

                if data_type_override := renderer_args.get("data_type"):
                    renderer_args["data_type"] = data_type_override.lower()

                # nautilai's processing handles normalization differently than mantarray's
                if metrics_output.metadata.instrument_type == InstrumentTypes.NAUTILAI:
                    renderer_args["normalize_y_axis"] = False

                # TODO remove all this try/finally + chdir once renderer accepts an output dir
                basedir = os.getcwd()
                try:
                    os.chdir(tmpdir)
                    output_filename = renderer.run(
                        metrics_output, OutputFormats.XLSX, output_format_args=renderer_args
                    )
                finally:
                    os.chdir(basedir)
                logger.info("Renderer complete")
            except Exception:
                error_msg = "Output file creation failed"
                logger.exception("Renderer failed")
                raise

            try:
                logger.info("Uploading renderer output")
                outfile_prefix = prefix.replace("uploads/", "analyzed/test-pulse3d/")
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

                if "user_defined_metadata" not in upload_meta:
                    user_defined_metadata = pre_analyzed_data.metadata.get("user_defined_metadata", {})
                    upload_meta["user_defined_metadata"] = user_defined_metadata
                    logger.info(f"Inserting user-defined metadata into DB: {user_defined_metadata}")

                    await con.execute(
                        "UPDATE uploads SET meta=$1 WHERE id=$2", json.dumps(upload_meta), upload_id
                    )
                else:
                    logger.info("Skipping insertion of user-defined metadata into DB")
            except Exception:
                # Tanner (9/28/23): not raising the exception here to avoid user-defined metadata issues stopping entire analyses
                logger.exception("Inserting user-defined metadata into DB failed")

            try:
                await insert_metadata_into_pg(
                    con,
                    pre_analyzed_data.metadata,
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

                logger.info("Inserted metadata into db")
            except Exception:
                logger.exception("Failed to insert metadata to db")
                raise

    except Exception as e:
        job_metadata["error"] = str(e)
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
        logger.info(f"Worker v{PULSE3D_VERSION} started")

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
        logger.info(f"Worker v{PULSE3D_VERSION} terminating")


if __name__ == "__main__":
    asyncio.run(main())
