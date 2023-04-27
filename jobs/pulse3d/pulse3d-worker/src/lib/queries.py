UPDATE_UPLOADS_TABLE = """
    UPDATE uploads SET bucket=$1, uploading_computer_name=$2, kilobytes=$3
    WHERE id=$4;
    """

INSERT_INTO_MANTARRAY_RECORDING_SESSIONS = """
    INSERT INTO mantarray_recording_sessions (mantarray_recording_session_id, upload_id, customer_id, user_id, instrument_serial_number, session_log_id, acquisition_started_at, length_microseconds,
    recording_started_at)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9);
    """


INSERT_INTO_MANTARRAY_SESSION_LOG_FILES = """
    INSERT INTO mantarray_session_log_files (session_log_id, bucket, object_key, upload_id, mantarray_recording_session_id, software_version, file_format_version, customer_id, user_id)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9);
    """
