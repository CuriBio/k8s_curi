import asyncio
import base64
import hashlib
import json
import logging
import os
import pkg_resources
import sys
import tempfile

import asyncpg
import boto3
import pandas as pd

from pulse3D.plate_recording import PlateRecording
from pulse3D.excel_writer import write_xlsx

from jobs import get_item, EmptyQueue
from lib.db import insert_metadata_into_pg, PULSE3D_UPLOADS_BUCKET

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

PULSE3D_VERSION = pkg_resources.get_distribution("pulse3D").version


def _load_from_dir(recording_dir, plate_recording_args):
    recordings = list(PlateRecording.from_directory(recording_dir, **plate_recording_args))
    logger.info(f"{len(recordings)} recording(s) found")
    return recordings


@get_item(queue=f"luci-pulse3d-v{PULSE3D_VERSION}")
async def process(con, item):
    logger.info(f"Processing item: {item}")
    s3_client = boto3.client("s3")
    job_metadata = {"processed_by": PULSE3D_VERSION}
    outfile_key = None
    try:
        try:
            upload_id = item["upload_id"]
            logger.info(f"Retrieving user ID and metadata for upload with ID: {upload_id}")

            query = (
                "SELECT users.customer_id, up.user_id, up.prefix, up.filename "
                "FROM uploads AS up JOIN users ON up.user_id = users.id "
                "WHERE up.id=$1"
            )

            upload_details = await con.fetchrow(query, upload_id)

            prefix = upload_details["prefix"]
            filename = upload_details["filename"]
            key = f"{prefix}/{filename}"

        except Exception as e:
            logger.exception(f"Fetching upload details failed: {e}")
            raise

        with tempfile.TemporaryDirectory(dir="/tmp") as tmpdir:
            logger.info(f"Downloading {PULSE3D_UPLOADS_BUCKET}/{key} to {tmpdir}/{filename}")

            try:
                s3_client.download_file(PULSE3D_UPLOADS_BUCKET, key, f"{tmpdir}/{filename}")
            except Exception as e:
                logger.exception(f"Failed to download: {e}")
                raise

            try:
                logger.info("Checking if time force data exists in s3")

                # adding prefix here representing the version of pulse3D used
                parquet_filename = f"{os.path.splitext(filename)[0]}.parquet"
                parquet_key = f"{prefix}/time_force_data/{PULSE3D_VERSION}/{parquet_filename}"
                parquet_path = os.path.join(tmpdir, parquet_filename)

                # attempt to download parquet file if recording has already been analyzed
                logger.info(f"Attempting to downloading {parquet_filename} to {parquet_path}")
                s3_client.download_file(PULSE3D_UPLOADS_BUCKET, parquet_key, parquet_path)
                re_analysis = True
            except Exception:  # continue with analysis even if original force data is not found
                logger.error(f"No existing data found for recording {parquet_filename}")
                re_analysis = False

            try:
                # remove params that were not given as these already have default values
                analysis_params = {
                    key: val
                    for key, val in json.loads(item["meta"])["analysis_params"].items()
                    if val is not None
                }

                # Tanner (10/7/22): popping these args out of analysis_params here since write_xlsx doesn't take them as a kwarg
                plate_recording_args = {
                    arg_name: analysis_params.pop(arg_name, None)
                    for arg_name in ("stiffness_factor", "inverted_post_magnet_wells")
                }

                logger.info("Starting pulse3d analysis")
                if re_analysis and not any(plate_recording_args.values()):
                    # if any plate recording args are provided, can't load from data frame since a re-analysis is required to recalculate the waveforms
                    logger.info(f"Loading previous time force data from {parquet_filename}")
                    existing_df = pd.read_parquet(parquet_path)
                    try:
                        recording = PlateRecording.from_dataframe(
                            os.path.join(tmpdir, filename), df=existing_df
                        )
                        recordings = list(recording)
                    except:
                        # If a user attempts to perform re-analysis on an analysis from < 0.25.2, it will fail
                        # because the parquet file won't have the raw data columns, so need to re-analyze
                        # TODO should rewrite parquet file with updated columns
                        logger.info(
                            f"Previous dataframe found is not compatible with v{PULSE3D_VERSION}, performing analysis again"
                        )
                        recordings = _load_from_dir(tmpdir, plate_recording_args)
                else:
                    recordings = _load_from_dir(tmpdir, plate_recording_args)

                # Tanner (6/8/22): only supports analyzing one recording at a time right now. Functionality can be added whenever analyzing multiple files becomes necessary
                first_recording = recordings[0]

                outfile = write_xlsx(first_recording, **analysis_params)
                outfile_prefix = prefix.replace("uploads/", "analyzed/")
            except Exception as e:
                logger.exception(f"Analysis failed: {e}")
                raise

            if re_analysis:
                logger.info("Skipping step to write time force data for upload")
            else:
                try:
                    logger.info("Writing time force data to parquet file for new upload")
                    first_recording.to_dataframe().to_parquet(parquet_path)

                    with open(parquet_path, "rb") as file:
                        contents = file.read()
                        md5 = hashlib.md5(contents).digest()
                        md5s = base64.b64encode(md5).decode()

                        logger.info(f"Uploading time force data to {parquet_key}")

                        s3_client.put_object(
                            Body=contents, Bucket=PULSE3D_UPLOADS_BUCKET, Key=parquet_key, ContentMD5=md5s
                        )
                except Exception as e:
                    logger.exception(f"Writing or uploading time force data failed: {e}")
                    raise

            with open(outfile, "rb") as file:
                try:
                    job_id = item["id"]
                    outfile_key = f"{outfile_prefix}/{job_id}/{outfile}"
                    logger.info(f"Uploading {outfile} to {PULSE3D_UPLOADS_BUCKET}/{outfile_key}")

                    contents = file.read()
                    md5 = hashlib.md5(contents).digest()
                    md5s = base64.b64encode(md5).decode()

                    s3_client.put_object(
                        Body=contents, Bucket=PULSE3D_UPLOADS_BUCKET, Key=outfile_key, ContentMD5=md5s
                    )
                except Exception as e:
                    logger.exception(f"Upload failed: {e}")
                    raise

                try:
                    logger.info(f"Inserting {outfile} metadata into db for upload {upload_id}")
                    await insert_metadata_into_pg(
                        con,
                        first_recording,
                        upload_details["customer_id"],
                        upload_details["user_id"],
                        upload_id,
                        file,
                        outfile_key,
                        md5s,
                        re_analysis,
                    )
                except Exception as e:
                    logger.exception(f"Failed to insert metadata to db for upload {upload_id}: {e}")
                    raise

    except Exception as e:
        job_metadata["error"] = f"{str(e)}: {item}"
        result = "error"
    else:
        logger.info(f"Job complete for upload {upload_id}")
        result = "finished"

    return result, job_metadata, outfile_key


async def main():
    try:
        logger.info(f"Worker v{PULSE3D_VERSION} started")

        # DB_PASS = os.getenv("POSTGRES_PASSWORD")
        # DB_USER = os.getenv("POSTGRES_USER", default="curibio_jobs")
        # DB_HOST = os.getenv("POSTGRES_SERVER", default="psql-rds.default")
        # DB_NAME = os.getenv("POSTGRES_DB", default="curibio")
        # dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
        dsn = "postgresql://root:HjnlH9RaeTt7uRuF7Uwco6BX4l0jgp39@localhost:5432/curibio"
        async with asyncpg.create_pool(dsn=dsn) as pool:
            async with pool.acquire() as con:
                while True:
                    try:
                        logger.info("Pulling job from queue")
                        await process(con=con)
                    except EmptyQueue as e:
                        logger.info(f"No jobs in queue: {e}")
                        return
                    except Exception as e:
                        logger.exception(f"Processing queue item failed: {repr(e)}")
                        return
    finally:
        logger.info(f"Worker v{PULSE3D_VERSION} terminating")


if __name__ == "__main__":
    asyncio.run(main())
