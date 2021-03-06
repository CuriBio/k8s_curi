import asyncio
import base64
import hashlib
import json
import logging
import os
import sys
import tempfile

import asyncpg
import boto3
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


@get_item(queue="pulse3d")
async def process(con, item):
    logger.info(f"Processing item: {item}")

    s3_client = boto3.client("s3")
    job_metadata = {}
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
                logger.info(f"Checking if time force data exists in s3")

                parquet_filename = f"{os.path.splitext(filename)[0]}.parquet"
                parquet_key = f"{prefix}/time_force_data/{parquet_filename}"
                parquet_path = os.path.join(tmpdir, parquet_filename)

                # attempt to download parquet file if recording has already been analyzed
                logger.info(f"Attempting to downloading {parquet_filename} to {tmpdir}/{parquet_filename}")
                s3_client.download_file(PULSE3D_UPLOADS_BUCKET, parquet_key, f"{tmpdir}/{parquet_filename}")
                re_analysis = True

            except Exception as e:  # continue with analysis even if original force data is not found
                logger.error(f"No existing data found for recording {parquet_filename}")
                re_analysis = False

            try:
                logger.info("Starting pulse3d analysis")
                recordings = list(PlateRecording.from_directory(tmpdir, not re_analysis))
                logger.info(f"{len(recordings)} recording(s) found")

                # remove params that were not given as these already have default values
                analysis_params = {
                    key: val
                    for key, val in json.loads(item["meta"])["analysis_params"].items()
                    if val is not None
                }

                if re_analysis:
                    logger.info(f"Loading previous time force data from {parquet_filename}")
                    recordings[0].load_time_force_data(parquet_path)

                # Tanner (6/8//22): only supports analyzing one recording at a time right now. Functionality can be added whenever analyzing multiple files becomes necessary
                outfile = write_xlsx(recordings[0], **analysis_params)
                outfile_prefix = prefix.replace("uploads/", "analyzed/")
            except Exception as e:
                logger.exception(f"Analysis failed: {e}")
                raise

            try:
                if not re_analysis:
                    logger.info("Writing time force data to parquet file for new upload")
                    time_force_dt, _ = recordings[0].write_time_force_csv(tmpdir)
                    time_force_dt.to_parquet(parquet_path)

                    with open(parquet_path, "rb") as file:
                        contents = file.read()
                        md5 = hashlib.md5(contents).digest()
                        md5s = base64.b64encode(md5).decode()

                        paraquet_key = f"{prefix}/time_force_data/{parquet_filename}"
                        logger.info(f"Uploading time force data to {paraquet_key}")

                        s3_client.put_object(
                            Body=contents, Bucket=PULSE3D_UPLOADS_BUCKET, Key=paraquet_key, ContentMD5=md5s
                        )
                else:
                    logger.info("Skipping step to write time force data for upload.")

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
                    logger.exception(f"Upload failed, {e}")
                    raise

                try:
                    logger.info(f"Inserting {outfile} metadata into db for upload {upload_id}")
                    for r in recordings:
                        await insert_metadata_into_pg(
                            con,
                            r,
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
        logger.info("Worker started")

        DB_PASS = os.getenv("POSTGRES_PASSWORD")
        DB_USER = os.getenv("POSTGRES_USER", default="curibio_jobs")
        DB_HOST = os.getenv("POSTGRES_SERVER", default="psql-rds.default")
        DB_NAME = os.getenv("POSTGRES_DB", default="curibio")

        dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
        async with asyncpg.create_pool(dsn=dsn) as pool:
            async with pool.acquire() as con:
                while True:
                    try:
                        logger.info(f"Pulling job from queue")
                        await process(con=con)
                    except EmptyQueue as e:
                        logger.info(f"No jobs in queue {e}")
                        return
                    except Exception as e:
                        logger.exception("Processing queue item failed")
                        return
    finally:
        logger.info("Worker terminating")


if __name__ == "__main__":
    asyncio.run(main())
