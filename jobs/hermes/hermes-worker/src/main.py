import asyncio
import datetime
from functools import wraps
import json
import os
import tempfile
import time
from typing import Any
from zipfile import ZipFile

import asyncpg
import boto3
from jobs import EmptyQueue
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars, merge_contextvars
from utils.s3 import upload_file_to_s3

from hermes import HERMES_VERSION, load_from_dir, longitudinal_aggregator, render


# insert into jobs_queue (sources, queue, priority, meta) values ('{"fe941b4b-46ec-42af-beb5-0a77f5ee4c1f", "16d2900f-a71a-4e9e-833e-daf5ed39fa15"}', 'hermes-v0.1.0rc0', 1, '{"platemaps": { "001": { "A1": "Control", "B1": "Control", "C1": "Control", "D1": "Control", "A2": "AAV6", "B2": "AAV6", "C2": "AAV6", "D2": "AAV6", "A3": "AAV9", "B3": "AAV9", "C3": "AAV9", "D3": "AAV9", "A4": "AAVMyo1", "B4": "AAVMyo1", "C4": "AAVMyo1", "D4": "AAVMyo1", "A5": "MyoAAV3a", "B5": "MyoAAV3a", "C5": "MyoAAV3a", "D5": "MyoAAV3a", "A6": "MyoAAV4a", "B6": "MyoAAV4a", "C6": "MyoAAV4a", "D6": "MyoAAV4a" } }, "platemap_assignments": { "fe941b4b-46ec-42af-beb5-0a77f5ee4c1f": "001", "16d2900f-a71a-4e9e-833e-daf5ed39fa15": "001" }, "analysis_params": { "experiment_start_time_utc": "2024-07-19 00:00:00", "local_tz_offset_hours": -7 }, "output_name": "test_output"}'::jsonb);

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
    inputs_dir: str, downloads_dir: str, upload_prefix: str, source_id: str, analysis_name: str
) -> dict[str, Any]:
    # input dir is the dir passed to hermes. It should only contain ready to load files (i.e. no zips)
    input_dir = os.path.join(inputs_dir, analysis_name)
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
    aggregate_metrics_file_path = os.path.join(input_dir, aggregate_metrics_filename)

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


# TODO move this into core lib
def get_secondary_item(*, queue):
    query = (
        "DELETE FROM jobs_queue "
        "WHERE id = (SELECT id FROM jobs_queue WHERE queue=$1 ORDER BY priority DESC, created_at ASC FOR UPDATE SKIP LOCKED LIMIT 1) "
        "RETURNING id, upload_id, created_at, meta"
    )

    def _outer(fn):
        @wraps(fn)
        async def _inner(*, con, con_to_update_job_result=None):
            async with con.transaction():
                item = await con.fetchrow(query, queue)
                if not item:
                    raise EmptyQueue(queue)

                # if con_to_update_job_result:
                #     # if already set to running, then assume that a different worker already tried processing the job and failed
                #     current_job_status = await con_to_update_job_result.fetchval(
                #         "SELECT status FROM jobs_result WHERE job_id=$1", item["id"]
                #     )
                #     if current_job_status == "running":
                #         await con_to_update_job_result.execute(
                #             "UPDATE jobs_result SET status='error', meta=meta||$1::jsonb, finished_at=NOW() WHERE job_id=$2",
                #             json.dumps({"error_msg": "Ran out of time/memory"}),
                #             item["id"],
                #         )
                #         return
                #
                #     await con_to_update_job_result.execute(
                #         "UPDATE jobs_result SET status='running', started_at=$1 WHERE job_id=$2",
                #         datetime.now(),
                #         item["id"],
                #     )

                ts = time.time()
                status, new_meta, object_key = await fn(con, item)
                runtime = time.time() - ts

                # update metadata
                meta = json.loads(item["meta"])
                meta.update(new_meta)

                # TODO delete this
                print(f"RESULT: {status=}, {runtime=}, {object_key=}, {meta=}")  # allow-print

                # data = {
                #     "status": status,
                #     "runtime": runtime,
                #     "finished_at": datetime.now(),
                #     "meta": json.dumps(meta),
                #     "object_key": object_key,
                # }
                # set_clause = ", ".join(f"{key} = ${i}" for i, key in enumerate(data, 1))
                # await con.execute(
                #     f"UPDATE jobs_result SET {set_clause} WHERE job_id=${len(data) + 1}",
                #     *data.values(),
                #     item["id"],
                # )

        return _inner

    return _outer


@get_secondary_item(queue=f"hermes-v{HERMES_VERSION}")
async def process_item(con, item):
    # keeping initial log without bound variables
    logger.info(f"Processing item: {item}")

    # TODO what else should be bound?
    bind_contextvars(job_id=item["id"])

    s3_client = boto3.client("s3")

    error_msg = None

    job_metadata = {}
    outfile_key = None

    try:
        logger.info("Processing submission metadata")
        try:
            submission_metadata = json.loads(item["meta"])
            sources = submission_metadata["sources"]
            platemaps = submission_metadata["platemaps"]
            platemap_assignments = submission_metadata["platemap_assignments"]
            hermes_analysis_params = submission_metadata["analysis_params"]
            hermes_analysis_params["experiment_start_time_utc"] = datetime.datetime.strptime(
                hermes_analysis_params["experiment_start_time_utc"], "%Y-%m-%d %H:%M:%S"
            )
            output_name = submission_metadata["output_name"]
        except:
            logger.exception("Error processing submission metadata")
            raise

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
                    fetched_source_info = await con.fetchrow(
                        "SELECT j.meta, j.object_key, j.finished_at, up.prefix "
                        "FROM jobs_result j JOIN uploads up ON j.upload_id=up.id "
                        "WHERE job_id=$1",
                        source_id,
                    )
                except:
                    logger.exception(f"Error fetching source details for ID: {source_id}")
                    raise

                logger.info(f"Processing source info for ID: {source_id}")
                source_info = {}
                try:
                    fetched_source_info = dict(fetched_source_info)
                    fetched_source_info_meta = json.loads(fetched_source_info["meta"])
                    logger.debug("Found %s", str(fetched_source_info))
                    analysis_filename = fetched_source_info["object_key"].split("/")[-1]
                    analysis_name = os.path.splitext(analysis_filename)[0]
                    source_info["p3d_analysis_metadata"] = {
                        "filename": analysis_filename,
                        "version": fetched_source_info_meta["version"],
                        "data_type": fetched_source_info_meta["data_type"],
                        "analysis_params": fetched_source_info_meta["analysis_params"],
                        "file_creation_timestamp": fetched_source_info["finished_at"],
                    }
                    source_info["platemap_name"] = platemap_assignments[source_id]
                    source_info["inputs"] = _create_file_info(
                        inputs_dir, downloads_dir, fetched_source_info["prefix"], source_id, analysis_name
                    )
                except:
                    logger.exception(f"Error processing source info for ID: {source_id}")
                    raise

                sources_info[analysis_name] = source_info

                logger.info(f"Downloading pre-analysis data for ID: {source_id}")
                try:
                    pre_analysis_info = source_info["inputs"]["pre_analysis"]
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
                    aggregate_metrics_info = source_info["inputs"]["aggregate_metrics"]
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
                # TODO delete this
                outputs_dir = "./test_output/"
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
