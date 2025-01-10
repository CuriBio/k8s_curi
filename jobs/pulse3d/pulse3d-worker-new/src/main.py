import asyncio
import json
import os
import tempfile
from typing import Any

import asyncpg
import boto3
import duckdb
import polars as pl
import structlog
from jobs import EmptyQueue, get_item
from mantarray_magnet_finding.exceptions import UnableToConvergeError
from curibio_analysis_lib import NormalizationMethods
from pulse3D import peak_finding, twitch_labelling
from pulse3D.constants import PACKAGE_VERSION as PULSE3D_VERSION
from pulse3D.data_loader import from_file, InstrumentTypes
from pulse3D.data_loader.utils import get_metadata_cls
from pulse3D.data_loader.metadata import BaseMetadata
from pulse3D.waveform_processing import pre_process, process, post_process, WAVEFORM_PROCESSING_SCHEMA
from pulse3d.utils.params import (
    WaveformProcessingParameters,
    PeakFindingParameters,
    TwitchLabellingParameters,
)
from structlog.contextvars import bind_contextvars, clear_contextvars, merge_contextvars

structlog.configure(
    processors=[
        merge_contextvars,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M.%S"),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()


# TODO see if this is needed
# duckdb.sql("CREATE SECRET s3_secret ( TYPE S3, PROVIDER CREDENTIAL_CHAIN, REGION 'us-east-2')")

PULSE3D_UPLOADS_BUCKET = os.getenv("UPLOADS_BUCKET_ENV", "test-pulse3d-uploads")


class QueryS3ParquetError(Exception):
    pass


class ExceptionWithErrorMsg(Exception):
    pass


WAVEFORM_PROCESSING_ADDITIONAL_SCHEMA = pl.Schema(
    {
        "upload_timestamp": pl.Datetime(time_unit="us", time_zone=None),
        "customer_id": str,
        "user_id": str,
        "upload_id": str,
        "job_id": str,
        "p3d_version": str,
    }
)
WAVEFORM_PROCESSING_FULL_SCHEMA = WAVEFORM_PROCESSING_SCHEMA | WAVEFORM_PROCESSING_ADDITIONAL_SCHEMA

PEAK_FINDING_ADDITIONAL_SCHEMA = WAVEFORM_PROCESSING_ADDITIONAL_SCHEMA | {"interactive_analysis": bool}
PEAK_FINDING_FULL_SCHEMA = peak_finding.PEAK_FINDING_SCHEMA | PEAK_FINDING_ADDITIONAL_SCHEMA

# Tanner (1/9/24): twitch labelling currently has same additional cols as peak finding
TWITCH_LABELLING_ADDITIONAL_SCHEMA = PEAK_FINDING_ADDITIONAL_SCHEMA
# Tanner (1/9/24): this may also contain "meta_<name>" cols of type str. These metadata cols should be applied after the additional schema cols
TWITCH_LABELLING_FULL_SCHEMA = twitch_labelling.TWITCH_LABELLING_SCHEMA | TWITCH_LABELLING_ADDITIONAL_SCHEMA


def apply_full_schema(
    df: pl.DataFrame, schema: pl.Schema, additional_col_vals: dict[str, Any]
) -> pl.DataFrame:
    # add additional col vals before applying schema, if anything isn't supposed to be there now it will get removed next
    df = df.with_columns(
        pl.lit(v).cast(schema[k]).alias(k) for k, v in additional_col_vals.items() if k in schema
    )
    metadata_cols = []
    if schema == TWITCH_LABELLING_FULL_SCHEMA:
        metadata_cols = sorted([c for c in df.columns if c.startswith("meta_")])

    return df.select(
        *[pl.col(c).cast(dtype) for c, dtype in schema.items()], *[pl.col(c).cast(str) for c in metadata_cols]
    )


def apply_p3d_schema(df: pl.DataFrame, schema: pl.Schema) -> pl.DataFrame:
    return df.select(*[pl.col(c).cast(dtype) for c, dtype in schema.items()])


def get_s3_parquet_file_name(job_details: dict[str, Any], upload_metadata: BaseMetadata) -> str:
    return f"{job_details['id']}_{upload_metadata.utc_beginning_recording}_{job_details['type']}"


def get_s3_parquet_path(
    job_details: dict[str, Any], pipeline_stage: str, file_name: str | None = None
) -> str:
    customer_id = job_details["customer_id"]
    if file_name is None:
        product = job_details["type"]
        file_name = f"*_{product}"
    return f"s3://{PULSE3D_UPLOADS_BUCKET}/{customer_id}/{pipeline_stage}/{file_name}.parquet"


def query_s3_parquet(query: str, *params: Any) -> pl.DataFrame:
    try:
        df = duckdb.sql(query, *params).pl()
    except Exception:
        raise QueryS3ParquetError()
    if df.is_empty():
        raise QueryS3ParquetError()
    return df.pl()


def upload_parquet_to_s3(df_upload: pl.DataFrame, s3_obj_key: str) -> None:
    duckdb.execute("COPY df_upload TO '$1'", s3_obj_key)


def handle_upload(
    df_analysis: pl.DataFrame,
    s3_parquet_file_name: str,
    job_details: dict[str, Any],
    pipeline_stage: str,
    additional_col_vals: dict[str, Any],
):
    match pipeline_stage:
        case "waveform_processing":
            schema = WAVEFORM_PROCESSING_FULL_SCHEMA
        case "peak_finding":
            schema = PEAK_FINDING_FULL_SCHEMA
        case "twitch_labelling":
            schema = TWITCH_LABELLING_FULL_SCHEMA
        case _:
            raise ValueError(f"Invalid pipeline stage: {pipeline_stage}")

    df_upload = apply_full_schema(df_analysis, schema, additional_col_vals)
    s3_obj_key = get_s3_parquet_path(job_details, pipeline_stage, s3_parquet_file_name)
    upload_parquet_to_s3(df_upload, s3_obj_key)

    logger.info(f"Uploaded {pipeline_stage} parquet file to {s3_obj_key}")


def get_analysis_params(
    job_metadata: dict[str, Any], upload_metadata: BaseMetadata
) -> tuple[WaveformProcessingParameters, PeakFindingParameters, TwitchLabellingParameters]:
    # remove params that were not given as these already have default values, and rename any params that have different names in the input containers
    rename_map = {
        "stiffness_factor": "post_stiffness_factor",
        "start_time": "window_start_time",
        "end_time": "window_end_time",
    }
    analysis_params = {
        rename_map.get(k, k): v for k, v in job_metadata["analysis_params"].items() if v is not None
    }
    # pull in overridable values from recording metadata if no override given
    for overridable_meta in ["data_type", "post_stiffness_factor"]:
        analysis_params[overridable_meta] = analysis_params.get(
            overridable_meta, upload_metadata.get(overridable_meta)
        )
    # mantarray always uses the same normalization
    if job_metadata["instrument_type"] == InstrumentTypes.MANTARRAY:
        analysis_params["normalization_method"] = NormalizationMethods.F_SUB_FMIN

    peak_finding_alg_args = {
        k: v
        for k in [
            "relative_prominence_factor",
            "noise_prominence_factor",
            "height_factor",
            "width_factors",
            "max_frequency",
            "valley_search_duration",
            "upslope_duration",
            "upslope_noise_allowance_duration",
        ]
        if (v := analysis_params.pop(k, None)) is not None
    }

    waveform_processing_params = WaveformProcessingParameters(**analysis_params)
    peak_finding_params = PeakFindingParameters(
        alg_args=peak_finding_alg_args  # currently no way to override any other params
    )
    twitch_labelling_params = TwitchLabellingParameters(**analysis_params)
    # TODO ignore platemap for now? Or convert real platemaps to new format for purpose of testing?

    return waveform_processing_params, peak_finding_params, twitch_labelling_params


async def load_details(con, item: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    logger.exception("Loading job and upload details")
    try:
        job_id = item["id"]
        upload_id = item["upload_id"]

        # currently contains id (upload), customer_id, user_id, prefix, filename, meta, created_at
        upload_details = dict(
            await con.fetchrow(
                """
                SELECT users.customer_id, up.user_id, up.prefix, up.filename, up.meta, up.created_at
                FROM uploads AS up JOIN users ON up.user_id = users.id
                WHERE up.id=$1
                """,
                upload_id,
            )
        )
        upload_details["id"] = upload_id

        # bind details to logger
        bind_contextvars(
            upload_id=str(upload_id),
            job_id=str(job_id),
            customer_id=str(upload_details["customer_id"]),
            user_id=str(upload_details["user_id"]),
        )

        # currently contains id (job), analysis_params, version (p3d), and name_override
        job_details = json.loads(item["meta"])
        job_details["id"] = job_id

        additional_col_vals = {
            "upload_timestamp": upload_details["customer_id"],
            "customer_id": upload_details["customer_id"],
            "user_id": upload_details["user_id"],
            "upload_id": upload_id,
            "job_id": job_id,
            "p3d_version": PULSE3D_VERSION,
            "interactive_analysis": None,  # this will be set later
        }
    except Exception:
        logger.exception("Failed loading job and upload details")
        raise

    return job_details, upload_details, additional_col_vals


def create_pre_processing_data(
    job_details: dict[str, Any],
    upload_details: dict[str, Any],
    s3_client,
    additional_col_vals: dict[str, Any],
) -> tuple[pl.DataFrame, BaseMetadata]:
    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info("Downloading recording file")
        try:
            upload_s3_key = f"{upload_details['prefix']}/{upload_details['filename']}"
            recording_path = f"{tmpdir}/{upload_details['filename']}"
            s3_client.download_file(PULSE3D_UPLOADS_BUCKET, upload_s3_key, recording_path)
            logger.info(f"Downloaded recording file to {recording_path}")
        except Exception:
            logger.exception("Failed to download recording file")
            raise

        logger.info("Running data-loader")
        try:
            loaded_data = from_file(recording_path)
        except Exception as e:
            logger.exception("Failed running data-loader")
            raise ExceptionWithErrorMsg("Loading recording data failed") from e

    logger.info("Running waveform-pre-processing")
    try:
        df_analysis = pre_process(loaded_data)
    except UnableToConvergeError as e:
        error_msg = "Unable to converge, low quality calibration data"
        logger.exception(error_msg)
        raise ExceptionWithErrorMsg(error_msg) from e
    except Exception as e:
        logger.exception("Failed running waveform-pre-processing")
        raise ExceptionWithErrorMsg("Waveform pre-processing failed") from e

    upload_metadata = loaded_data.metadata

    s3_parquet_file_name = get_s3_parquet_file_name(job_details, upload_metadata)
    handle_upload(df_analysis, s3_parquet_file_name, job_details, "waveform_processing", additional_col_vals)

    return df_analysis, upload_metadata


def validate_product(df_analysis: pl.DataFrame, job_details: dict[str, Any]) -> None:
    logger.info("Verifying product type in DF matches product type in DB")
    try:
        product_df = df_analysis["product"][0]
        product_db = job_details["type"]
    except Exception:
        logger.exception("Error getting product type")
        raise

    if product_df != product_db:
        error_msg = f"Product type in DF ({product_df}) does not match product type in DB ({product_db})"
        logger.exception(error_msg)
        raise Exception(error_msg)


@get_item(queue=f"pulse3d-v{PULSE3D_VERSION}")
async def process_item(con, item):
    # keeping initial log without bound variables
    logger.info(f"Processing item: {item}")

    s3_client = boto3.client("s3")
    job_metadata = {"processed_by": PULSE3D_VERSION}  # sanity check

    # Tanner (3/27/24): this is specifically for human-readable error messages. The actual message in the exception is handled separately
    error_msg = None

    try:
        job_details, upload_details, additional_col_vals = await load_details(con, item)

        # try to download existing waveform pre-processing data, otherwise create and upload it
        logger.info("Checking for existing waveform-pre-processing data in S3")
        try:
            df_analysis = query_s3_parquet(
                "SELECT * FROM read_parquet('$1') WHERE upload_id=$2 AND p3d_version=$3",
                get_s3_parquet_path(job_details, "waveform_pre_processing"),
                upload_details["id"],
                PULSE3D_VERSION,
            )
            logger.info("Retrieved existing waveform-pre-processing data from S3")
            upload_metadata: BaseMetadata = get_metadata_cls(dict(upload_details["meta"]))
        except QueryS3ParquetError:
            logger.info("No existing waveform-pre-processing data found in S3, creating")
            df_analysis, upload_metadata = create_pre_processing_data(
                job_details, upload_details, s3_client, additional_col_vals
            )
        except Exception:
            logger.exception("Error loading existing waveform-pre-processing data, recreating")
            df_analysis, upload_metadata = create_pre_processing_data(
                job_details, upload_details, s3_client, additional_col_vals
            )

        validate_product(df_analysis, job_details)

        s3_parquet_file_name = get_s3_parquet_file_name(job_details, upload_metadata)

        waveform_processing_params, peak_finding_params, twitch_labelling_params = get_analysis_params(
            job_metadata, upload_metadata
        )

        # create and upload waveform processing data
        logger.info("Running waveform-processing")
        try:
            df_analysis = process(df_analysis, waveform_processing_params)
        except Exception:
            error_msg = "Waveform processing failed"
            logger.exception("Failed running waveform-processing")
            raise

        logger.info("Uploading waveform-processing results")
        try:
            handle_upload(
                df_analysis, s3_parquet_file_name, job_details, "waveform_processing", additional_col_vals
            )
        except Exception:
            logger.exception("Failed uploading waveform-processing results")
            raise

        # create waveform post-processing data
        logger.info("Running waveform-post-processing")
        try:
            df_analysis = post_process(df_analysis, waveform_processing_params)
        except Exception:
            error_msg = "Waveform post-processing failed"
            logger.exception("Failed running waveform-post-processing")
            raise

        # check for IA data in S3 for this job, if not found then run peak finding. In either case, upload
        # result of peak finding module
        logger.info("Checking for IA data in S3")
        try:
            # TODO figure out how we want to store IA data in S3 and then update this query
            query_s3_parquet(
                "SELECT * FROM read_parquet('$1') WHERE FALSE",
                get_s3_parquet_path(job_details, "interactive_analysis"),
            )
            logger.info("Retrieved IA data from S3")
            additional_col_vals["interactive_analysis"] = True
            # TODO should the peak/valley data just be passed into peak_finding so it can handle it on its own?
            # might also be easier to enforce schema that way
            logger.info("Loaded data from IA")
        except QueryS3ParquetError:
            logger.info("No IA data found in S3")
            additional_col_vals["interactive_analysis"] = False

            logger.info("Running peak-finding")
            try:
                df_analysis = peak_finding.run(df_analysis, peak_finding_params)
            except Exception:
                error_msg = "Peak detection failed"
                logger.exception("Failed running peak-finding")
                raise
        except Exception:
            error_msg = "Loading interactive analysis data failed"
            logger.exception("Failed loading IA data")
            raise

        logger.info("Uploading peak-finding results")
        try:
            handle_upload(df_analysis, s3_parquet_file_name, job_details, "peak_finding", additional_col_vals)
        except Exception:
            logger.exception("Failed uploading peak-finding results")
            raise

        # create and upload twitch labelling data
        logger.info("Running twitch-labelling")
        try:
            df_analysis = twitch_labelling.run(df_analysis, twitch_labelling_params)
        except Exception:
            error_msg = "Twitch labelling failed"
            logger.exception("Failed running twitch-labelling")
            raise

        logger.info("Uploading twitch-labelling results")
        try:
            handle_upload(
                df_analysis, s3_parquet_file_name, job_details, "twitch_labelling", additional_col_vals
            )
        except Exception:
            logger.exception("Failed uploading twitch-labelling results")
            raise

        # handle metadata
        logger.info("Checking for new metadata to add for upload in DB")
        try:
            existing_upload_metadata = json.loads(upload_details["meta"])

            # letting pydantic convert to JSON will handle serialization of all data types, so do that and then load into a dict
            upload_metadata_dict = json.loads(upload_metadata.model_dump_json())
            new_meta = {
                k: upload_metadata_dict[k]
                for k in (upload_metadata_dict.keys() - existing_upload_metadata.keys())
            }
            if new_meta:
                logger.info(f"Adding metadata to upload in DB: {new_meta}")
                upload_metadata |= new_meta
                await con.execute(
                    "UPDATE uploads SET meta=$1 WHERE id=$2",
                    json.dumps(upload_metadata),
                    upload_details["id"],
                )
            else:
                logger.info("No upload metadata to update in DB")
        except Exception:
            # Tanner (7/29/24): don't raise the exception, no reason this should cause the whole analysis to fail
            logger.exception("Failed updating metadata of upload in DB")

        logger.info("Updating job metadata")
        try:
            job_metadata |= {
                "plate_barcode": upload_metadata.plate_barcode,
                "recording_length_ms": upload_metadata.full_recording_length,
                "data_type": waveform_processing_params.data_type,
            }
            if upload_metadata.instrument_type == InstrumentTypes.MANTARRAY:
                job_metadata["stim_barcode"] = upload_metadata.stim_barcode
        except Exception:
            logger.exception("Failed updating job metadata")
            raise

    except ExceptionWithErrorMsg as e:
        job_metadata["error"] = repr(e.__cause__)
        result = "error"
        job_metadata["error_msg"] = str(e)
    except Exception as e:
        job_metadata["error"] = repr(e)
        result = "error"
        # some errors do not include an error message
        if error_msg:
            job_metadata["error_msg"] = error_msg
    else:
        logger.info("Job complete")
        result = "finished"

    # resetting logging for subsequent jobs
    clear_contextvars()

    # Tanner (1/8/24): there is currently no rendering step being executed, so return None for s3 key of renderer output
    return result, job_metadata, None


async def main():
    try:
        logger.info(f"Pulse3D Worker v{PULSE3D_VERSION} started")

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
                        logger.exception("Failed processing queue item")
                        return
    finally:
        logger.info(f"Pulse3D Worker v{PULSE3D_VERSION} terminating")


if __name__ == "__main__":
    asyncio.run(main())
