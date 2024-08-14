import asyncio
import os
import tempfile
from typing import Any
from zipfile import ZipFile

import asyncpg
import boto3
from jobs import EmptyQueue, get_item
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars, merge_contextvars
from utils.s3 import upload_file_to_s3

from hermes import HERMES_VERSION, load_from_dir, longitudinal_aggregator, render


PULSE3D_UPLOADS_BUCKET = os.getenv("UPLOADS_BUCKET_ENV", "test-pulse3d-uploads")


structlog.configure(
    processors=[
        merge_contextvars,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M.%S"),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()


def _create_file_info(
    inputs_dir: str, downloads_dir: str, upload_prefix: str, source_id: str
) -> dict[str, Any]:
    # input dir is the dir passed to hermes. It should only contain ready to load files (i.e. no zips)
    input_dir = os.path.join(downloads_dir, source_id)
    os.mkdir(input_dir)
    # download dir is used for processing downloads like zip files.
    download_dir = os.path.join(downloads_dir, source_id)
    os.mkdir(download_dir)

    pre_analysis_dir = os.path.join(download_dir, "pre-analysis")
    os.mkdir(pre_analysis_dir)
    pre_analysis_filename = "pre-analysis.zip"
    pre_analysis_file_s3_key = f"{upload_prefix}/{source_id}/{pre_analysis_filename}"
    pre_analysis_file_path = os.path.join(pre_analysis_dir, pre_analysis_filename)

    aggregate_metrics_filename = "aggregate_metrics.parquet"
    aggregate_metrics_s3_key = f"{upload_prefix}/{source_id}/{aggregate_metrics_filename}"
    # no processing required for a parquet file, so put it straight into the inputs dir
    aggregate_metrics_file_path = os.path.join(inputs_dir, aggregate_metrics_filename)

    return {
        "input_dir": input_dir,
        "pre_analysis": {
            "dir": pre_analysis_dir,
            "filename": pre_analysis_filename,
            "file_path": pre_analysis_file_path,
            "s3_key": pre_analysis_file_s3_key,
        },
        "aggregate_metrics": {
            "filename": aggregate_metrics_filename,
            "file_path": aggregate_metrics_file_path,
            "s3_key": aggregate_metrics_s3_key,
        },
    }


@get_item(queue=f"hermes-v{HERMES_VERSION}")
async def process_item(con, item):
    # keeping initial log without bound variables
    logger.info(f"Processing item: {item}")

    # TODO what else should be bound?
    bind_contextvars(job_id=item["job_id"])

    s3_client = boto3.client("s3")

    error_msg = None

    job_metadata = {}
    outfile_key = None

    try:
        # TODO should platemaps be files or stored in metadata?
        # meta = {
        #     "sources": ["job_id_1", ...],
        #     "platemaps": {"pm1": {...}, ...},
        #     "platemap_assignments": {"job_id_1": "pm1", ...}
        #     "analysis_params": {"experiment start": ..., "local tz offset hrs": ..., ?}
        #     "output_name": "name"
        # }

        submission_metadata = item["meta"]
        sources = submission_metadata["sources"]
        platemaps = submission_metadata["platemaps"]
        platemap_assignments = submission_metadata["platemap_assignments"]
        hermes_analysis_params = submission_metadata["analysis_params"]
        output_name = submission_metadata["output_name"]

        sources_info = {}

        with tempfile.TemporaryDirectory() as tmpdir:
            inputs_dir = os.path.join(tmpdir, "inputs")
            os.mkdir(inputs_dir)
            downloads_dir = os.path.join(tmpdir, "downloads")
            os.mkdir(downloads_dir)
            outputs_dir = os.path.join(tmpdir, "outputs")
            os.mkdir(outputs_dir)
            # retrieve and format info of sources, download aggregate metrics and metadata files
            for source_id in sources:
                logger.info(f"Fetching source details for ID: {source_id}")
                try:
                    fetched_source_info = await con.fetch(
                        "SELECT j.meta, j.object_key, j.finished_at, up.prefix "
                        "FROM jobs_result j JOIN uploads up ON j.upload_id=up.id "
                        "WHERE job_id=$1",
                        source_id,
                    )
                except:
                    logger.exception(f"Error fetching source details for ID: {source_id}")
                    raise

                logger.info(f"Processing source details for ID: {source_id}")
                source_info = {}
                try:
                    fetched_source_info = dict(fetched_source_info)
                    analysis_filename = fetched_source_info["object_key"].split("/")[-1]
                    analysis_name = os.path.splitext(analysis_filename)[0]
                    source_info["analysis_meta"] = {
                        "filename": analysis_filename,
                        "version": fetched_source_info["meta"]["version"],
                        "data_type": fetched_source_info["meta"]["data_type"],
                        "analysis_params": fetched_source_info["meta"]["analysis_params"],
                        "file_creation_timestamp": fetched_source_info["finished_at"],
                    }
                    source_info["platemap_name"] = platemap_assignments[source_id]
                    source_info["inputs"] = _create_file_info(
                        inputs_dir, downloads_dir, fetched_source_info["prefix"], source_id
                    )
                except:
                    logger.exception(f"Error processing source details for ID: {source_id}")
                    raise

                sources_info[analysis_name] = source_info

                logger.info(f"Downloading pre-analysis data for ID: {source_id}")
                try:
                    pre_analysis_info = source_info[source_id]["inputs"]["pre_analysis"]
                    s3_client.download_file(
                        PULSE3D_UPLOADS_BUCKET, pre_analysis_info["s3_key"], pre_analysis_info["file_path"]
                    )
                except:
                    logger.exception(f"Error downloading pre-analysis file for ID: {source_id}")
                    raise
                logger.info(f"Moving metadata from pre-analysis zip to input dir for ID: {source_id}")
                try:
                    with ZipFile(pre_analysis_info["file_path"]) as z:
                        z.extract("metadata.json", path=source_info["inputs"]["input_dir"])
                except:
                    logger.exception(
                        f"Error moving metadata from pre-analysis zip to input dir for ID: {source_id}"
                    )
                    raise
                logger.info(f"Downloading aggregate metrics for ID: {source_id}")
                try:
                    aggregate_metrics_info = source_info[source_id]["inputs"]["aggregate_metrics"]
                    s3_client.download_file(
                        PULSE3D_UPLOADS_BUCKET,
                        aggregate_metrics_info["s3_key"],
                        aggregate_metrics_info["file_path"],
                    )
                except:
                    logger.exception(f"Error downloading aggregate metrics file for ID: {source_id}")
                    raise

            logger.info("Loading source files")
            try:
                # TODO eventually platemaps will be stored in S3 and should be downloaded from there
                input_containers = load_from_dir(inputs_dir, sources_info, platemaps)
            except:
                logger.exception("Failed loading source files")
                raise

            logger.info("Running longitudinal aggregation")
            try:
                combined_container = longitudinal_aggregator(
                    input_containers,
                    hermes_analysis_params["experiment_start_time_utc"],
                    hermes_analysis_params["local_tz_offset_hours"],
                )
            except:
                logger.exception("Failed running longitudinal aggregation")
                raise

            logger.info("Running renderer")
            try:
                render(combined_container, output_name, output_dir=outputs_dir)
            except:
                error_msg = "Output file creation failed"
                logger.exception("Failed running renderer")
                raise

            # TODO upload renderer output
            upload_file_to_s3
            outfile_key = "TODO"

    except Exception as e:
        job_metadata["error"] = str(e)
        result = "error"
        # some errors do not include an error message
        if error_msg:
            job_metadata["error_msg"] = error_msg
    else:
        logger.info("Job complete")
        result = "finished"

    clear_contextvars()

    return result, job_metadata, outfile_key


async def main():
    try:
        logger.info(f"Hermes Worker v{HERMES_VERSION} started")

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
        logger.info(f"Hermes Worker v{HERMES_VERSION} terminating")


if __name__ == "__main__":
    asyncio.run(main())
