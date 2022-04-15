import logging
import os
import sys

from .queries import INSERT_INT0_UPLOADED_S3_OBJECTS
from .queries import INSERT_INTO_MANTARRAY_RAW_FILES
from .queries import INSERT_INTO_MANTARRAY_RECORDING_SESSIONS
from .queries import INSERT_INTO_MANTARRAY_SESSION_LOG_FILES
from .queries import INSERT_INTO_S3_OBJECTS

from .utils import get_s3_object_contents
from .utils import load_data_to_df

LOGS_BUCKET = os.environ.get(
    "LOGS_BUCKET_ENV", "test-mantarray-logs"
)  # I just need the bucket name, I don't need extra permissions
PULSE3D_UPLOADS_BUCKET = os.getenv("UPLOADS_BUCKET_ENV", "test-sdk-upload")

# set up custom basic config
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO, stream=sys.stdout
)
logger = logging.getLogger(__name__)


async def insert_metadata_into_pg(con, pr, file, outfile_key, md5s):
    """
    args:
        contains pgpool connection, PlateRecording, <file>.xlsx, object key for outfile, and the md5 hash
    """
    try:
        metadata, well_data = load_data_to_df(file, pr)
        s3_size = get_s3_object_contents(PULSE3D_UPLOADS_BUCKET, outfile_key)
        customer_account_id = outfile_key.split("/")[0]
        user_account_id = outfile_key.split("/")[1]
    except Exception as e:
        raise Exception(f"in formatting: {e}")

    logger.info("Executing queries to the database in relation to aggregated metadata")
    try:
        await con.execute(
            INSERT_INT0_UPLOADED_S3_OBJECTS,
            PULSE3D_UPLOADS_BUCKET,
            outfile_key,
            metadata["uploading_computer_name"],
        )
    except Exception as e:
        raise Exception(f"in uploaded_s3_objects: {e}")

    try:
        logger.info("Inserting recording session metadata")
        await con.execute(
            INSERT_INTO_MANTARRAY_RECORDING_SESSIONS,
            metadata["mantarray_recording_session_id"],
            customer_account_id,
            user_account_id,
            metadata["instrument_serial_number"],
            metadata["session_log_id"],
            metadata["acquisition_started_at"].replace(
                tzinfo=None
            ),  # required otherwise postgres errors about timezone
            metadata["length_microseconds"],
            metadata["recording_started_at"].replace(tzinfo=None),
        )
    except Exception as e:
        raise Exception(f"in mantarray_recording_sessions: {e}")

    try:
        logger.info("Inserting s3 object metadata")
        await con.execute(INSERT_INTO_S3_OBJECTS, s3_size, md5s)
    except Exception as e:
        raise Exception(f"in s3_objects: {e}")

    try:
        logger.info("Inserting log metadata")
        log_session_key = f"{customer_account_id}/{metadata['session_log_id']}.zip"
        await con.execute(
            INSERT_INTO_MANTARRAY_SESSION_LOG_FILES,
            metadata["session_log_id"],
            LOGS_BUCKET,
            log_session_key,
            metadata["mantarray_recording_session_id"],
            metadata["software_version"],
            metadata["file_format_version"],
            customer_account_id,
            user_account_id,
        )
    except Exception as e:
        raise Exception(f"in mantarray_session_log_files: {e}")

    try:
        logger.info("Inserting individual well data")
        for well in well_data:
            await con.execute(
                INSERT_INTO_MANTARRAY_RAW_FILES,
                well["well_index"],
                well["length_microseconds"],
                well["recording_started_at"].replace(tzinfo=None),
                metadata["mantarray_recording_session_id"],
            )
    except Exception as e:
        raise Exception(f"in mantarray_raw_files: {e}")

    logger.info("DB complete")
