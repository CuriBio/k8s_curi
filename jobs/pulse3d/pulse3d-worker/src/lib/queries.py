INSERT_INT0_UPLOADED_S3_OBJECTS = """
    INSERT INTO uploaded_s3_objects(bucket, object_key, upload_started_at, uploading_computer_name)
    VALUES ($1, $2, NOW(), $3);
    """

SELECT_LAST_UPLOAD_ID = """(SELECT id FROM uploaded_s3_objects ORDER BY id DESC LIMIT 1)"""

INSERT_INTO_MANTARRAY_RECORDING_SESSIONS = """
    INSERT INTO mantarray_recording_sessions(mantarray_recording_session_id, customer_account_id, user_account_id, instrument_serial_number, session_log_id, acquisition_started_at, length_microseconds,
    recording_started_at)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
    """

INSERT_INTO_MANTARRAY_RAW_FILES = f"""
    INSERT INTO mantarray_raw_files(well_index, upload_id, length_microseconds, recording_started_at, mantarray_recording_session_id)
    VALUES ($1, {SELECT_LAST_UPLOAD_ID}, $2, $3, $4);
    """

INSERT_INTO_S3_OBJECTS = f"""
    INSERT INTO s3_objects(upload_id, kilobytes, md5) VALUES ({SELECT_LAST_UPLOAD_ID}, $1, $2);
    """

INSERT_INTO_MANTARRAY_SESSION_LOG_FILES = f"""
    INSERT INTO mantarray_session_log_files(session_log_id, bucket, object_key, upload_id, mantarray_recording_session_id, software_version, file_format_version, customer_account_id, user_account_id) VALUES ($1, $2, $3, {SELECT_LAST_UPLOAD_ID},$4, $5, $6, $7, $8);
"""
