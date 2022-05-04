import logging
import os

from .queries import UPDATE_UPLOADS_TABLE
from .queries import INSERT_INTO_MANTARRAY_RECORDING_SESSIONS
from .queries import INSERT_INTO_MANTARRAY_SESSION_LOG_FILES

from .utils import get_s3_object_contents
from .utils import load_data_to_df

MANTARRAY_LOGS_BUCKET = os.environ.get("MANTARRAY_LOGS_BUCKET_ENV", "test-mantarray-logs")
PULSE3D_UPLOADS_BUCKET = os.getenv("UPLOADS_BUCKET_ENV", "test-sdk-upload")

logger = logging.getLogger(__name__)


async def insert_metadata_into_pg(con, pr, upload_id, file, outfile_key, md5s):
    """
    args:
        contains pgpool connection, PlateRecording, <file>.xlsx, object key for outfile, and the md5 hash
    """
    try:
        metadata = load_data_to_df(file, pr)
        s3_size = get_s3_object_contents(PULSE3D_UPLOADS_BUCKET, outfile_key)

        customer_id, user_id = outfile_key.split("/")[-3:-1]
    except Exception as e:
        raise Exception(f"in formatting: {repr(e)}")

    logger.info("Executing queries to the database in relation to aggregated metadata")
    async with con.transaction():
        try:
            await con.execute(
                UPDATE_UPLOADS_TABLE,
                PULSE3D_UPLOADS_BUCKET,
                outfile_key,
                metadata["uploading_computer_name"],
                s3_size,
                md5s,
                upload_id,
            )
        except Exception as e:
            raise Exception(f"in uploads: {repr(e)}")

        try:
            logger.info("Inserting recording session metadata")
            await con.execute(
                INSERT_INTO_MANTARRAY_RECORDING_SESSIONS,
                metadata["mantarray_recording_session_id"],
                upload_id,
                customer_id,
                user_id,
                metadata["instrument_serial_number"],
                metadata["session_log_id"],
                # timezone required otherwise postgres errors
                metadata["acquisition_started_at"].replace(tzinfo=None),
                metadata["length_microseconds"],
                metadata["recording_started_at"].replace(tzinfo=None),
            )
        except Exception as e:
            raise Exception(f"in mantarray_recording_sessions: {repr(e)}")

        try:
            logger.info("Inserting log metadata")
            log_session_key = f"{customer_id}/{metadata['session_log_id']}.zip"
            await con.execute(
                INSERT_INTO_MANTARRAY_SESSION_LOG_FILES,
                metadata["session_log_id"],
                MANTARRAY_LOGS_BUCKET,
                log_session_key,
                upload_id,
                metadata["mantarray_recording_session_id"],
                metadata["software_version"],
                metadata["file_format_version"],
                customer_id,
                user_id,
            )
        except Exception as e:
            raise Exception(f"in mantarray_session_log_files: {repr(e)}")

    logger.info("DB complete")
