import logging
import os

from .queries import UPDATE_UPLOADS_TABLE
from .queries import INSERT_INTO_MANTARRAY_RECORDING_SESSIONS
from .queries import INSERT_INTO_MANTARRAY_SESSION_LOG_FILES

from .utils import get_s3_object_contents
from .utils import load_data_to_df

MANTARRAY_LOGS_BUCKET = os.environ.get("MANTARRAY_LOGS_BUCKET_ENV", "test-mantarray-logs")
PULSE3D_UPLOADS_BUCKET = os.getenv("UPLOADS_BUCKET_ENV", "test-pulse3d-uploads")
logger = logging.getLogger(__name__)


async def insert_metadata_into_pg(
    con, pr, customer_id, user_id, upload_id, file, outfile_key, md5s, re_analysis
):
    """
    TODO fix this, use standard docstyle
    args:
        contains pgpool connection, PlateRecording, <file>.xlsx, object key for outfile, and the md5 hash
    """
    try:
        metadata = load_data_to_df(file, pr)
        s3_size = get_s3_object_contents(PULSE3D_UPLOADS_BUCKET, outfile_key)
    except Exception as e:
        raise Exception(f"in formatting: {repr(e)}")

    async with con.transaction():
        if not re_analysis:
            logger.info("Updating uploads table")
            try:
                await con.execute(
                    UPDATE_UPLOADS_TABLE,
                    PULSE3D_UPLOADS_BUCKET,
                    metadata["uploading_computer_name"],
                    s3_size,
                    md5s,
                    upload_id,
                )
            except Exception as e:
                raise Exception(f"in uploads: {repr(e)}")
        else:
            logger.info("Skipping update of uploads table")

        try:
            logger.info("Inserting recording session metadata")

            # timezone required otherwise postgres errors
            for datetime_key in ("acquisition_started_at", "recording_started_at"):
                if metadata[datetime_key] is not None:
                    metadata[datetime_key] = metadata[datetime_key].replace(tzinfo=None)

            await con.execute(
                INSERT_INTO_MANTARRAY_RECORDING_SESSIONS,
                metadata["mantarray_recording_session_id"],
                upload_id,
                customer_id,
                user_id,
                metadata["instrument_serial_number"],
                metadata["session_log_id"],
                metadata["acquisition_started_at"],
                metadata["length_microseconds"],
                metadata["recording_started_at"],
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
    return metadata["plate_barcode"], metadata["stim_barcode"], metadata["length_microseconds"]
