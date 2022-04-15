import asyncio
import json
import logging
import os
import base64
import hashlib
import tempfile
import asyncpg
import boto3

from pulse3D.plate_recording import PlateRecording
from pulse3D.excel_writer import write_xlsx

from jobs import get_item, EmptyQueue

from lib.db import insert_metadata_into_pg

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

PULSE3D_UPLOADS_BUCKET = os.getenv("UPLOADS_BUCKET_ENV", "test-sdk-upload")


@get_item(queue="pulse3d")
async def process(con, item):
    query = "SELECT user_id, meta FROM uploads WHERE id=$1"
    s3_client = boto3.client("s3")

    try:
        upload_id = item.get("upload_id")
        upload = await con.fetchrow(query, upload_id)

        meta = json.loads(upload.get("meta"))
        user_id = upload.get("user_id")
        logger.info(f"Found jobs for user {user_id} with meta {json.dumps(meta)}")

        prefix = meta["prefix"]
        filename = meta["filename"]
        key = f"{prefix}/{filename}"
    except Exception as e:
        logger.exception("Fetching upload details failed")
        return ("error", {})

    with tempfile.TemporaryDirectory(dir="/tmp") as tmpdir:
        logger.info(f"Downloading {PULSE3D_UPLOADS_BUCKET}/{key} to {tmpdir}/{filename}")
        try:
            s3_client.download_file(PULSE3D_UPLOADS_BUCKET, key, f"{tmpdir}/{filename}")
        except Exception as e:
            logger.exception(f"Failed to download: {e}")
            return ("error", {})

        try:
            logger.info(f"Starting pulse3d analysis")
            outfile = f"{'.'.join(filename.split('.')[:-1])}.xlsx"
            prs = PlateRecording.from_directory(tmpdir)
            pr = next(prs)
            write_xlsx(pr, name=outfile)
        except Exception as e:
            logger.exception(f"Analysis failed")
            return ("failed", {})

        with open(outfile, "rb") as file:
            try:
                logger.info(f"Uploading {outfile} to {PULSE3D_UPLOADS_BUCKET}/{outfile}")
                contents = file.read()
                md5 = hashlib.md5(contents).digest()
                md5s = base64.b64encode(md5).decode()

                outfile_key = f"{prefix}/{outfile}"
                s3_client.put_object(
                    Body=contents, Bucket=PULSE3D_UPLOADS_BUCKET, Key=outfile_key, ContentMD5=md5s
                )
            except Exception as e:
                logger.exception(f"Upload failed, {e}")
                return ("error", {})

            try:
                logger.info(f"Inserting {outfile} metadata into db")
                await insert_metadata_into_pg(con, pr, file, outfile_key, md5s)
            except Exception as e:
                logger.error(f"Failed to insert metadata to db: {e}")
                return ("error inserting into db", {})

    return ("finished", {})


async def main():
    DB_PASS = os.getenv("POSTGRES_PASSWORD")
    DB_USER = os.getenv("POSTGRES_USER", default="curibio_jobs")
    DB_HOST = os.getenv("POSTGRES_SERVER", default="psql-rds.default")
    DB_NAME = os.getenv("POSTGRES_DB", default="curibio")

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
    asyncio.run(main())
