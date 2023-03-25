import boto3
import datetime
import pandas as pd
import uuid

from pulse3D.constants import BACKEND_LOG_UUID
from pulse3D.constants import STIM_BARCODE_UUID
from pulse3D.constants import COMPUTER_NAME_HASH_UUID
from pulse3D.constants import MANTARRAY_SERIAL_NUMBER_UUID
from pulse3D.constants import MICRO_TO_BASE_CONVERSION
from pulse3D.constants import PLATE_BARCODE_UUID
from pulse3D.constants import SOFTWARE_RELEASE_VERSION_UUID
from pulse3D.constants import UTC_BEGINNING_DATA_ACQUISTION_UUID
from pulse3D.constants import UTC_BEGINNING_RECORDING_UUID


def load_data_to_df(file_name, pr):
    df = pd.read_excel(file_name, sheet_name=None, engine="openpyxl")
    time_series = df["continuous-waveforms"]["Time (seconds)"].dropna()
    recording_length = round(time_series.iloc[-1] * MICRO_TO_BASE_CONVERSION)

    return format_metadata(df["metadata"], pr, recording_length)


def format_metadata(meta_sheet, pr, recording_length: int):
    first_available_well = next(iter(pr))
    return {
        "plate_barcode": first_available_well.get(PLATE_BARCODE_UUID, "NA"),
        "recording_started_at": first_available_well[UTC_BEGINNING_RECORDING_UUID],
        "file_format_version": first_available_well.version,
        "instrument_serial_number": first_available_well.get(MANTARRAY_SERIAL_NUMBER_UUID),
        "length_microseconds": recording_length,
        "file_creation_timestamp": meta_sheet.iloc[11, 2],
        "mantarray_recording_session_id": uuid.uuid4(),
        "uploading_computer_name": first_available_well.get(COMPUTER_NAME_HASH_UUID),
        # fails if not a datetime
        "acquisition_started_at": first_available_well.get(
            UTC_BEGINNING_DATA_ACQUISTION_UUID, datetime.datetime.now()
        ),
        "session_log_id": first_available_well.get(BACKEND_LOG_UUID, ""),
        # this value is non-nullable in at least one table so need to return an empty string if not found
        "software_version": first_available_well.get(SOFTWARE_RELEASE_VERSION_UUID),
        "stim_barcode": first_available_well.get(STIM_BARCODE_UUID),
    }


def get_s3_object_contents(bucket: str, key: str):
    # Grab s3 object metadata from aws
    s3_client = boto3.client("s3")
    try:
        # Get content size in bytes to kb
        return s3_client.head_object(Bucket=bucket, Key=key).get("ContentLength") / 1000
    except Exception as e:
        raise Exception(f"error retrieving s3 object size: {e}")
