"""
Check uploads table in DB for rows which do not have metadata set. Use pulse3D to extract the metadata from
the recording files and update the rows.
"""

import asyncio
import boto3
import json
import logging
import os
import sys
import tempfile

import asyncpg
from pulse3D import data_loader

PULSE3D_UPLOADS_BUCKET = os.getenv("TEST_UPLOADS_BUCKET", "test-pulse3d-uploads")
BATCH_SIZE = 10

DRY_RUN = True


logging.basicConfig(
    format="[%(asctime)s.%(msecs)03d] [%(levelname)s] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)


logger = logging.getLogger()
s3_client = boto3.client("s3")


class DummyCon:
    def __init__(self, con):
        self._con = con
        self._transaction = None

    async def fetch(self, *args):
        if self._transaction:
            self._transaction.statements.append(("FETCH:", *args))
        # need to actually run this
        return await self._con.fetch(*args)

    async def execute(self, *args):
        if self._transaction:
            self._transaction.statements.append(("EXECUTE:", *args))

    def transaction(self):
        self._transaction = DummyTransaction()
        return self._transaction


class DummyTransaction:
    def __init__(self):
        self.statements = []

    async def __aenter__(self):
        self.statements = [("BEGIN",)]
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.statements.append(("COMMIT",))
        statements_str = [tuple(str(item) for item in statement) for statement in self.statements]
        pretty_statements = json.dumps(statements_str, indent=4)
        logger.info(f"DRY RUN:\n{pretty_statements}")


async def main():
    update_count = 0
    try:
        logger.info("START")

        DB_PASS = os.getenv("POSTGRES_PASSWORD")
        DB_USER = os.getenv("POSTGRES_USER", default="curibio_jobs")
        DB_HOST = os.getenv("POSTGRES_SERVER", default="psql-rds.default")
        DB_NAME = os.getenv("POSTGRES_DB", default="curibio")

        dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"

        async with asyncpg.create_pool(dsn=dsn) as pool:
            async with pool.acquire() as con:
                if DRY_RUN:
                    con = DummyCon(con)
                offset = 0
                while update_inc := await run(con, offset, BATCH_SIZE):
                    update_count += update_inc
                    offset += BATCH_SIZE

    finally:
        logger.info(f"updated {update_count} uploads")
        logger.info("DONE")


async def run(con, offset, limit):
    logger.info(f"processing uploads {offset}-{offset+limit}")
    update_count = 0

    async with con.transaction():
        uploads = await con.fetch(
            "SELECT id, prefix, filename FROM uploads "
            "WHERE meta->>'recording_name' IS NULL "  # assume that if recording_name is not set then the metadata needs to be updated
            "ORDER BY created_at DESC OFFSET $1 LIMIT $2",
            offset,
            limit,
        )
        for upload_details in uploads:
            upload_id = upload_details["id"]
            try:
                await process_upload(upload_details, con)
            except Exception:
                logger.exception(f"failed to update upload {upload_id}")
            else:
                update_count += 1

    return update_count


async def process_upload(upload_details, con):
    prefix = upload_details["prefix"]
    upload_filename = upload_details["filename"]

    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info("downloading recording")
        try:
            key = f"{prefix}/{upload_filename}"
            recording_path = f"{tmpdir}/{upload_filename}"
            s3_client.download_file(PULSE3D_UPLOADS_BUCKET, key, recording_path)
            logger.info(f"downloaded recording file to {recording_path}")
        except Exception:
            logger.info("failed to download recording zip file")
            raise

        logger.info("running data loader")
        try:
            loaded_data = data_loader.from_file(recording_path)
        except Exception:
            logger.info("failed to load data")
            raise

        logger.info("dumping metadata to json")
        try:
            metadata_json = loaded_data.metadata.model_dump_json()
        except Exception:
            logger.info("failed to create metadata json")
            raise

        logger.info("updating DB")
        try:
            await con.execute("UPDATE uploads SET meta=$1 WHERE id=$2", metadata_json, upload_details["id"])
        except Exception:
            logger.info("failed to update metadata in DB")
            raise


if __name__ == "__main__":
    asyncio.run(main())
