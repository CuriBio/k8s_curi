"""
Check uploads table in DB for rows which do not have metadata set. Use pulse3D to extract the metadata from
the recording files and update the rows.
"""

import asyncio
import datetime

import boto3
import logging
import os
import sys
import tempfile

import asyncpg
from pulse3D import metrics

PULSE3D_UPLOADS_BUCKET = os.getenv("TEST_UPLOADS_BUCKET")

DRY_RUN = True

s3_client = boto3.client("s3")


logging.basicConfig(
    format="[%(asctime)s.%(msecs)03d] [%(levelname)s] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(
            os.path.join(
                "logs", f"extract_metadata__{datetime.datetime.utcnow().strftime('%Y_%m_%d__%H_%M_%S')}.log"
            )
        ),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger()


async def main():
    logger.info("START")

    job_counts = {"total": 0, "success": 0, "failed": 0, "skipped": 0}

    try:
        DB_PASS = os.getenv("POSTGRES_PASSWORD")
        DB_USER = os.getenv("POSTGRES_USER", default="curibio_jobs")
        DB_HOST = os.getenv("POSTGRES_SERVER", default="psql-rds.default")
        DB_NAME = os.getenv("POSTGRES_DB", default="curibio")

        dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"

        async with asyncpg.create_pool(dsn=dsn) as pool:
            async with pool.acquire() as con:
                all_jobs = await con.fetch(
                    "select * from jobs_result where meta->>'version' like '1.0%' and meta->>'version' not like '%rc%' and status='finished' order by created_at desc"
                )
                job_counts["total"] = len(all_jobs)
                logger.info(f"found {len(all_jobs)} jobs")
                for job_info in all_jobs:
                    res = process_job(job_info)
                    job_counts[res] += 1
    finally:
        logger.info(f"result: {job_counts}")
        logger.info("DONE")


def process_job(job_info) -> str:
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            if not DRY_RUN:
                "TODO"
        return "success"
    except:
        logger.exception("TODO")
        return "failed"


if __name__ == "__main__":
    asyncio.run(main())
