"""
Check uploads table in DB for rows which do not have metadata set. Use pulse3D to extract the metadata from
the recording files and update the rows.
"""

import asyncio
import boto3
import datetime
import json
import logging
import logging.config
import os
import tempfile

import asyncpg
from pulse3D import data_loader
import structlog

PULSE3D_UPLOADS_BUCKET = os.getenv("TEST_UPLOADS_BUCKET")
BATCH_SIZE = 10

DRY_RUN = True

s3_client = boto3.client("s3")

# Have to do this complicated setup in order to get structlog to write to both stdout and a file
# https://www.structlog.org/en/stable/standard-library.html#rendering-using-structlog-based-formatters-within-logging
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "default": {"level": "INFO", "class": "logging.StreamHandler"},
            "file": {
                "level": "INFO",
                "class": "logging.handlers.WatchedFileHandler",
                "filename": os.path.join(
                    "logs",
                    f"extract_upload_metadata__{datetime.datetime.utcnow().strftime('%Y_%m_%d__%H_%M_%S')}.log",
                ),
            },
        },
        "loggers": {"": {"handlers": ["default", "file"], "level": "INFO", "propagate": True}},
    }
)
structlog.configure(
    processors=[
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S.%f"),
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(colors=False),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()


class DummyCon:
    def __init__(self, con):
        self._con = con
        self._transaction = None

    async def fetch(self, *args):
        if self._transaction:
            self._transaction.statements.append(("FETCH:", *[str(a) for a in args]))
        # need to actually run this
        return await self._con.fetch(*args)

    async def execute(self, *args):
        if self._transaction:
            self._transaction.statements.append(("EXECUTE:", *[str(a) for a in args]))

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
        pretty_statements = json.dumps(self.statements, indent=4)
        logger.info(f"DRY RUN:\n{pretty_statements}")


async def main():
    logger.info("START")
    logger.info(f"{DRY_RUN=}")

    update_count = 0
    failure_count = 0
    total_uploads_to_process = 0

    try:

        DB_PASS = os.getenv("POSTGRES_PASSWORD")
        DB_USER = os.getenv("POSTGRES_USER", default="curibio_jobs")
        DB_HOST = os.getenv("POSTGRES_SERVER", default="psql-rds.default")
        DB_NAME = os.getenv("POSTGRES_DB", default="curibio")

        dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"

        async with asyncpg.create_pool(dsn=dsn) as pool:
            async with pool.acquire() as con:
                total_uploads_to_process = await con.fetchval(
                    "SELECT count(*) FROM uploads WHERE meta->>'recording_name' IS NULL"
                )

                if total_uploads_to_process == 0:
                    logger.info("no uploads to process")
                    return

                if DRY_RUN:
                    con = DummyCon(con)

                total_processed = 0
                while total_processed < total_uploads_to_process:
                    logger.info(
                        f"processing uploads {total_processed}-{total_processed+BATCH_SIZE} / {total_uploads_to_process}"
                    )
                    # offset by the failure count since successful jobs will not show up in the query, and thus do not
                    # need to be taken into consideration when determining the offset
                    update_inc, failed_inc = await run(con, failure_count, BATCH_SIZE)
                    update_count += update_inc
                    failure_count += failed_inc
                    total_processed = update_count + failure_count
    finally:
        logger.info(f"result: {total_uploads_to_process=}, {update_count=}, {failure_count=}")
        logger.info("DONE")


async def run(con, offset, limit):
    update_count = 0
    failure_count = 0

    uploads = await con.fetch(
        "SELECT id, prefix, filename FROM uploads "
        "WHERE meta->>'recording_name' IS NULL "  # assume that if recording_name is not set then the metadata needs to be updated
        "ORDER BY created_at DESC OFFSET $1 LIMIT $2",
        offset,
        limit,
    )

    async with con.transaction():
        for upload_details in uploads:
            try:
                await process_upload(upload_details, con)
            except Exception:
                logger.exception(f"failed to update upload {upload_details['id']}")
                failure_count += 1
            else:
                update_count += 1

    return update_count, failure_count


async def process_upload(upload_details, con):
    prefix = upload_details["prefix"]
    upload_filename = upload_details["filename"]

    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info(f"downloading recording for ID: {upload_details['id']}")
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
