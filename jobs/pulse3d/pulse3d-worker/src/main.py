import asyncio
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

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

PULSE3D_UPLOADS_BUCKET = os.getenv("UPLOADS_BUCKET_ENV", "test-sdk-upload")

@get_item(queue="pulse3d")
async def process(con, item):
    query = "SELECT user_id, meta FROM uploads WHERE id=$1" 
    s3_client = boto3.client("s3")

    try:
        upload_id = item.get("upload_id")
        upload = con.fetchrow(query, upload_id)

        meta = json.loads(upload.get("meta"))
        user_id = upload.get("user_id")

        bucket_name = f"{PULSE3D_UPLOADS_BUCKET}/{user_id}/{meta["path"]}/{meta["file_name"]}"
        key = f"{user_id}/{meta["path"]}/{meta["file_name"]}"
    except Exception as e:
        logger.exception("Fetching upload details failed")
        return


    with tempfile.TemporaryDirectory(dir="/tmp") as tmpdir:
        logger.info(f"Downloading {PULSE3D_UPLOADS_BUCKET}/{key} to {tmpdir}")
        s3_client.download_file(PULSE3D_UPLOADS_BUCKET, key, f"{tmpdir}/{key}")

        try:
            logger.info(f"Starting pulse3d analysis")
            prs = PlateRecording.from_directory(f"/{tmpdir}")
            for r in prs:
                write_xlsx(r, name="test_recording.xlsx")
        except Exception as e:
            logger.exception(f"Analysis failed")
            return

        with open(f"test_recording.xlsx", "rb") as f:
            try:
                logger.info(f"Uploading test_recording.xlsx to {PULSE3D_UPLOADS_BUCKET}/test_recording.xlsx")
                contents = f.read()
                s3_client.put_object(Body=f, Bucket=PULSE3D_UPLOADS_BUCKET, Key="test_recording.xlsx")
            except Exception as e:
                logger.exception(f"Upload failed")
                return


async def main():
    DB_PASS = os.getenv("DB_PASS")
    DB_USER = os.getenv("DB_USER", default="curibio_jobs")
    DB_HOST = os.getenv("DB_HOST", default="psql-rds.default")
    DB_NAME = os.getenv("DB_NAME", default="curibio")

    dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
    async with asyncpg.create_pool(dsn=dsn) as pool:
        async with pool.acquire() as con:
            while True:
                try:
                    await process(con=con)
                except EmptyQueue as e:
                    logger.info(f"No jobs in queue {e}")
                    return
                except Exception as e:
                    logger.exception("Processing queue item failed")
                    return


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
