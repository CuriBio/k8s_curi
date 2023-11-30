import boto3
import os
import structlog
import uuid

from .queries import UPDATE_UPLOADS_TABLE
from .queries import INSERT_INTO_MANTARRAY_RECORDING_SESSIONS
from .queries import INSERT_INTO_MANTARRAY_SESSION_LOG_FILES

MANTARRAY_LOGS_BUCKET = os.environ.get("MANTARRAY_LOGS_BUCKET_ENV", "test-mantarray-logs")
PULSE3D_UPLOADS_BUCKET = os.getenv("UPLOADS_BUCKET_ENV", "test-pulse3d-uploads")
# will automatically have the bound variables from main.py
logger = structlog.getLogger()


def _get_s3_object_contents(bucket: str, key: str):
    # Grab s3 object metadata from aws
    s3_client = boto3.client("s3")
    try:
        # Get content size in bytes to kb
        return s3_client.head_object(Bucket=bucket, Key=key).get("ContentLength") / 1000
    except Exception as e:
        raise Exception(f"error retrieving s3 object size: {e}")


async def insert_metadata_into_pg(con, metadata, customer_id, user_id, upload_id, outfile_key, re_analysis):
    """
    TODO fix this, use standard docstyle
    args:
        contains pgpool connection, metadata, <file>.xlsx, and object key for outfile
    """
    try:
        # metadata = load_data_to_df(file, metadata)
        mantarray_recording_session_id = uuid.uuid4()
        s3_size = _get_s3_object_contents(PULSE3D_UPLOADS_BUCKET, outfile_key)
    except Exception as e:
        raise Exception(f"in formatting: {repr(e)}")

    async with con.transaction():
        if not re_analysis:
            logger.info("Updating uploads table")
            try:
                await con.execute(
                    UPDATE_UPLOADS_TABLE,
                    PULSE3D_UPLOADS_BUCKET,
                    metadata.computer_name_hash,
                    s3_size,
                    upload_id,
                )
            except Exception as e:
                raise Exception(f"in uploads: {repr(e)}")
        else:
            logger.info("Skipping update of uploads table")

        try:
            logger.info("Inserting recording session metadata")

            await con.execute(
                INSERT_INTO_MANTARRAY_RECORDING_SESSIONS,
                mantarray_recording_session_id,
                upload_id,
                customer_id,
                user_id,
                metadata.instrument_serial_number,
                metadata.software_session_log_id,
                metadata.utc_beginning_data_acquisition.replace(tzinfo=None),
                metadata.full_recording_length,
                metadata.utc_beginning_recording.replace(tzinfo=None),
            )
        except Exception as e:
            raise Exception(f"in mantarray_recording_sessions: {repr(e)}")

        try:
            logger.info("Inserting log metadata")
            log_session_key = f"{customer_id}/{metadata.software_session_log_id}.zip"

            await con.execute(
                INSERT_INTO_MANTARRAY_SESSION_LOG_FILES,
                metadata.software_session_log_id,
                MANTARRAY_LOGS_BUCKET,
                log_session_key,
                upload_id,
                mantarray_recording_session_id,
                metadata.software_release_version,
                metadata.file_format_version,
                customer_id,
                user_id,
            )
        except Exception as e:
            raise Exception(f"in mantarray_session_log_files: {repr(e)}")

    logger.info("DB complete")
