import asyncio
from copy import deepcopy
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
from pulse3D.data_loader import (
    MantarrayBeta1Metadata,
    MantarrayBeta2Metadata,
    from_file,
    InstrumentTypes,
    BaseMetadata,
)
from pulse3D.pre_analysis import PreAnalyzedData, process
from pulse3D.rendering import OutputFormats
from semver import VersionInfo
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

PULSE3D_VERSION = "v1.0.0rc9"


def _get_existing_metadata(metadata_dict: dict[str, Any]) -> BaseMetadata:
    is_beta_2 = metadata_dict["file_format_version"] >= VersionInfo.parse("1.0.0")

    if metadata_dict["instrument_type"] == InstrumentTypes.NAUTILUS:
        return BaseMetadata(**metadata_dict)
    elif is_beta_2:
        return MantarrayBeta2Metadata(**metadata_dict)
    else:
        return MantarrayBeta1Metadata(**metadata_dict)


# needs to be prefixed so that the queue processor doesn't pick it up
@get_item(queue=f"test-pulse3d-{PULSE3D_VERSION}")
async def process_item(con, item):
    # keeping initial log without bound variables
    logger.info(f"Processing item: {item}")

    s3_client = boto3.client("s3")
    job_metadata = {"processed_by": PULSE3D_VERSION}
    outfile_key = None

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
        except Exception:
            logger.exception("Fetching upload details failed")
            raise

        with tempfile.TemporaryDirectory(dir="/tmp") as tmpdir:
            zipped_recording_filename = f"{os.path.splitext(upload_filename)[0]}.zip"
            zipped_recording_key = f"{prefix}/time_force_data/{PULSE3D_VERSION}/{zipped_recording_filename}"
            zipped_recording_path = os.path.join(tmpdir, zipped_recording_filename)

            stim_waveforms_path = os.path.join(tmpdir, "stim_waveforms.parquet")
            tissue_waveforms_path = os.path.join(tmpdir, "tissue_waveforms.parquet")
            metadata_path = os.path.join(tmpdir, "metadata.json")

            features_parquet_key = f"{prefix}/{job_id}/peaks_valleys.parquet"
            features_filepath = os.path.join(tmpdir, "peaks_valleys.parquet")

            try:
                key = f"{prefix}/{upload_filename}"
                recording_path = f"{tmpdir}/{analysis_filename}"
                s3_client.download_file(PULSE3D_UPLOADS_BUCKET, key, recording_path)
                logger.info(f"Downloaded recording file to {recording_path}")
            except Exception:
                logger.exception("Failed to download recording zip file")
                raise

            try:
                # attempt to download peaks and valleys from s3, will only be the case for interactive analysis jobs
                s3_client.download_file(PULSE3D_UPLOADS_BUCKET, features_parquet_key, features_filepath)
                interactive_analysis = True
                logger.info(f"Downloaded peaks and valleys to {features_filepath}")
            except Exception:  # TODO catch only boto3 errors here
                logger.info("No existing peaks and valleys found for recording")

            try:
                s3_client.download_file(PULSE3D_UPLOADS_BUCKET, zipped_recording_key, zipped_recording_path)
                logger.info(f"Downloaded existing preanalyed data to {zipped_recording_path}")

                with ZipFile(zipped_recording_path) as z:
                    z.extractall(tmpdir)

                tissue_waveforms = pl.read_parquet(tissue_waveforms_path)
                stim_waveforms = (
                    pl.read_parquet(stim_waveforms_path) if os.path.exists(stim_waveforms_path) else None
                )

                metadata_dict = json.load(open(metadata_path))
                existing_metadata = _get_existing_metadata(metadata_dict)

                pre_analyzed_data = PreAnalyzedData(
                    tissue_waveforms=tissue_waveforms,
                    stim_waveforms=stim_waveforms,
                    metadata=existing_metadata,
                )

                re_analysis = True
            except Exception:  # TODO catch only boto3 errors here
                logger.info(f"No existing data found for recording {zipped_recording_filename}")

            # remove params that were not given as these already have default values
            analysis_params = {k: v for k, v in metadata["analysis_params"].items() if v is not None}

            if not re_analysis:
                try:
                    logger.info("Starting dataloader")
                    loaded_data = from_file(recording_path)
                except Exception:
                    logger.exception("DataLoader failed")
                    raise

                try:
                    logger.info("Starting preanalysis")
                    pre_analyzed_data = process(loaded_data)
                except UnableToConvergeError:
                    raise Exception("Unable to converge due to low quality of data")
                except Exception:
                    logger.exception("PreAnalysis failed")
                    raise

                try:
                    # TODO cleanup
                    zipfile = "pre_analysis_data.zip"
                    with ZipFile(zipfile, "w") as z:
                        for field in ("tissue_waveforms", "stim_waveforms"):
                            df = getattr(pre_analyzed_data, field)
                            if df is not None:  # stim_waveforms can be None
                                parquet_filepath = os.path.join(tmpdir, f"{field}.parquet")
                                df.write_parquet(parquet_filepath)
                                z.write(parquet_filepath, f"{field}.parquet")

                        with open(metadata_path, "w") as f:
                            f.write(pre_analyzed_data.metadata.model_dump_json())

                        z.write(metadata_path, "metadata.json")

                    upload_file_to_s3(bucket=PULSE3D_UPLOADS_BUCKET, key=zipped_recording_key, file=zipfile)
                    logger.info("Uploaded preanalyzed data to S3")
                except Exception:
                    logger.exception("Upload failed")
                    raise

            try:
                # copy so that windowed data isn't written to S3 and used on following recordings
                windowed_pre_analyzed_data = deepcopy(pre_analyzed_data)
                tissue_data = windowed_pre_analyzed_data.tissue_waveforms
                stim_data = windowed_pre_analyzed_data.stim_waveforms

                for window, filter_fn in (
                    ("start_time", lambda x: pl.col("time") >= x),
                    ("end_time", lambda x: pl.col("time") <= x),
                ):
                    if (time_sec := analysis_params.get(window)) is not None:
                        tissue_data = tissue_data.filter(filter_fn(time_sec))
                        if stim_data is not None:
                            stim_data = stim_data.filter(filter_fn(time_sec))

                windowed_pre_analyzed_data.tissue_waveforms = tissue_data
                windowed_pre_analyzed_data.stim_waveforms = stim_data
            except Exception:
                logger.exception("Error windowing tissue data")

            try:
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
                logger.info("Running peak detector")
                data_with_features = peak_finder.run(windowed_pre_analyzed_data, alg_args=peak_detector_args)
            except Exception:
                logger.exception("PeakDetector failed")
                raise

            if not interactive_analysis:
                try:
                    data_with_features.tissue_features.write_parquet(features_filepath)
                    upload_file_to_s3(
                        bucket=PULSE3D_UPLOADS_BUCKET, key=features_parquet_key, file=features_filepath
                    )
                    logger.info(f"Uploaded features to {PULSE3D_UPLOADS_BUCKET}/{features_parquet_key}")
                except Exception:
                    logger.exception("Upload failed")
                    raise

            try:
                # TODO sync these values
                # twitch_widths v. widths --- baseline_widths_to_use v. baseline_widths
                metrics_args = {
                    arg_name: val
                    for arg_name, orig_name in (
                        ("widths", "twitch_widths"),
                        ("baseline_widths", "baseline_widths_to_use"),
                        ("well_groups", "well_groups"),
                    )
                    if (val := analysis_params.get(orig_name)) is not None
                }
                logger.info("Running metrics")
                metrics_output = metrics.run(data_with_features, **metrics_args)
            except Exception:
                logger.exception("Metrics failed")
                raise

            try:
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

                logger.info("Running renderer")
                output_filename = renderer.run(
                    metrics_output, OutputFormats.XLSX, output_format_args=renderer_args
                )
            except Exception:
                logger.exception("Renderer failed")
                raise

            try:
                outfile_prefix = prefix.replace("uploads/", "analyzed/test-pulse3d/")
                outfile_key = f"{outfile_prefix}/{job_id}/{output_filename}"
                upload_file_to_s3(bucket=PULSE3D_UPLOADS_BUCKET, key=outfile_key, file=output_filename)
                logger.info(f"Uploaded {output_filename} to {PULSE3D_UPLOADS_BUCKET}/{outfile_key}")
            except Exception:
                logger.exception("Upload failed")
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

                job_metadata |= {
                    "plate_barcode": pre_analyzed_data.metadata.plate_barcode,
                    "stim_barcode": pre_analyzed_data.metadata.stim_barcode,
                    "recording_length_ms": pre_analyzed_data.metadata.full_recording_length,
                }

                logger.info("Inserted metadata into db")
            except Exception:
                logger.exception("Failed to insert metadata to db")
                raise

    except Exception as e:
        job_metadata["error"] = f"{str(e)}"
        result = "error"
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
