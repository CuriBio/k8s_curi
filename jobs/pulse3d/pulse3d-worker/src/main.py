import asyncio
import base64
import hashlib
import json
import os
import pkg_resources
import tempfile
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars, merge_contextvars

import asyncpg
import boto3
import pandas as pd
import numpy as np

from pulse3D.constants import MICRO_TO_BASE_CONVERSION
from pulse3D.constants import WELL_NAME_UUID
from pulse3D.constants import PLATEMAP_LABEL_UUID
from pulse3D.constants import DATA_TYPE_UUID
from pulse3D.constants import NOT_APPLICABLE_LABEL
from pulse3D.constants import USER_DEFINED_METADATA_UUID
from pulse3D.exceptions import (
    DuplicateWellsFoundError,
    InvalidValleySearchDurationError,
    TooFewPeaksDetectedError,
)
from pulse3D.exceptions import IncorrectOpticalFileFormatError
from pulse3D.excel_writer import write_xlsx
from pulse3D.nb_peak_detection import noise_based_peak_finding
from pulse3D.plate_recording import PlateRecording
from mantarray_magnet_finding.exceptions import UnableToConvergeError

from jobs import get_item, EmptyQueue
from utils.s3 import upload_file_to_s3
from lib.queries import SELECT_UPLOAD_DETAILS
from lib.db import insert_metadata_into_pg, PULSE3D_UPLOADS_BUCKET

structlog.configure(
    processors=[
        merge_contextvars,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M.%S"),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.getLogger()

PULSE3D_VERSION = pkg_resources.get_distribution("pulse3D").version


def _load_from_dir(recording_dir, plate_recording_args):
    recordings = list(PlateRecording.from_directory(recording_dir, **plate_recording_args))
    logger.info(f"{len(recordings)} recording(s) found")
    return recordings


# TODO move this to core lib
def _is_valid_well_name(well_name):
    return (
        isinstance(well_name, str)
        and len(well_name) in (2, 3)
        and well_name[0].isalpha()
        and well_name[1].isdigit()
    )


@get_item(queue=f"pulse3d-v{PULSE3D_VERSION}")
async def process(con, item):
    # keeping initial log without bound variables
    logger.info(f"Processing item: {item}")

    s3_client = boto3.client("s3")
    job_metadata = {"processed_by": PULSE3D_VERSION}
    outfile_key = None

    try:
        try:
            job_id = item["id"]
            upload_id = item["upload_id"]
            upload_details = await con.fetchrow(SELECT_UPLOAD_DETAILS, upload_id)

            # bind details to logger
            bind_contextvars(
                upload_id=str(upload_id),
                job_id=str(job_id),
                customer_id=str(upload_details["customer_id"]),
                user_id=str(upload_details["user_id"]),
            )

            logger.info("Starting job")

            prefix = upload_details["prefix"]
            metadata = json.loads(item["meta"])

            upload_filename = upload_details["filename"]
            # if a new name has been given in the upload form, then replace here, else use original name
            analysis_filename = (
                f"{name_override}.zip"
                if (name_override := metadata.get("name_override"))
                else upload_filename
            )

            key = f"{prefix}/{upload_filename}"

        except Exception:
            logger.exception("Fetching upload details failed")
            raise

        with tempfile.TemporaryDirectory(dir="/tmp") as tmpdir:
            # adding prefix here representing the version of pulse3D used
            parquet_filename = f"{os.path.splitext(upload_filename)[0]}.parquet"
            parquet_key = f"{prefix}/time_force_data/{PULSE3D_VERSION}/{parquet_filename}"
            parquet_path = os.path.join(tmpdir, parquet_filename)
            # set variables for where peaks and valleys should be or where it will go in s3
            pv_parquet_key = f"{prefix}/{job_id}/peaks_valleys.parquet"
            pv_temp_path = os.path.join(tmpdir, "peaks_valleys.parquet")

            try:
                s3_client.download_file(PULSE3D_UPLOADS_BUCKET, key, f"{tmpdir}/{analysis_filename}")
                logger.info(f"Downloaded {PULSE3D_UPLOADS_BUCKET}/{key} to {tmpdir}/{analysis_filename}")
            except Exception:
                logger.exception("Failed to download recording zip file")
                raise

            try:
                # attempt to download parquet file if recording has already been analyzed
                s3_client.download_file(PULSE3D_UPLOADS_BUCKET, parquet_key, parquet_path)
                re_analysis = True

                logger.info(f"Downloaded {parquet_filename} to {parquet_path}")
            except Exception:  # TODO catch only boto3 errors here
                logger.info(f"No existing data found for recording {parquet_filename}")
                re_analysis = False

            try:
                # attempt to download peaks and valleys from s3, will only be the case for interactive analysis jobs
                s3_client.download_file(PULSE3D_UPLOADS_BUCKET, pv_parquet_key, pv_temp_path)
                interactive_analysis = True

                logger.info(f"Downloaded peaks and valleys to {pv_temp_path}")
            except Exception:  # TODO catch only boto3 errors here
                logger.info("No existing peaks and valleys found for recording")
                interactive_analysis = False

            try:
                # remove params that were not given as these already have default values
                analysis_params = {
                    key: val for key, val in metadata["analysis_params"].items() if val is not None
                }

                # Tanner (10/7/22): popping these args out of analysis_params here since write_xlsx doesn't take them as a kwarg
                plate_recording_args = {
                    arg_name: analysis_params.pop(arg_name, None)
                    for arg_name in ("stiffness_factor", "inverted_post_magnet_wells", "well_groups")
                }

                # well groups should always be added regardless of reanalysis
                well_groups = plate_recording_args.get("well_groups")
                use_existing_time_v_force = re_analysis and not any(plate_recording_args.values())

                logger.info("Starting pulse3d analysis")
                if use_existing_time_v_force:
                    # if any plate recording args are provided, can't load from data frame since a re-analysis is required to recalculate the waveforms
                    recording_df = pd.read_parquet(parquet_path)

                    try:
                        recording = PlateRecording.from_dataframe(
                            os.path.join(tmpdir, analysis_filename),
                            recording_df=recording_df,
                            well_groups=well_groups,
                        )
                        recordings = list(recording)
                    except:
                        # If a user attempts to perform re-analysis on an analysis from < 0.25.2, it will fail
                        # because the parquet file won't have the raw data columns, so need to re-analyze
                        logger.exception(
                            f"Previous dataframe found is not compatible with v{PULSE3D_VERSION}, performing analysis again"
                        )
                        recordings = _load_from_dir(tmpdir, plate_recording_args)
                        re_analysis = False
                else:
                    recordings = _load_from_dir(tmpdir, plate_recording_args)

                # Tanner (6/8/22): only supports analyzing one recording at a time right now. Functionality can be added whenever analyzing multiple files becomes necessary
                first_recording = recordings[0]
            except (DuplicateWellsFoundError, IncorrectOpticalFileFormatError):
                # raise unique error to be shown in FE for this specific type of exception
                logger.exception("Invalid file format")
                raise
            except UnableToConvergeError:
                raise Exception("Unable to converge due to low quality of data")
            except Exception:
                logger.exception("PlateRecording failed")
                raise

            # if metadata is not set yet, set it here
            try:
                upload_meta = json.loads(upload_details["meta"])

                if "user_defined_metadata" not in upload_meta:
                    user_defined_metadata = json.loads(
                        first_recording.wells[0].get(USER_DEFINED_METADATA_UUID, r"{}")
                    )

                    logger.info(f"Inserting user-defined metadata into DB: {user_defined_metadata}")
                    upload_meta["user_defined_metadata"] = user_defined_metadata

                    await con.execute(
                        "UPDATE uploads SET meta=$1 WHERE id=$2", json.dumps(upload_meta), upload_id
                    )
                else:
                    logger.info("Skipping insertion of user-defined metadata into DB")
            except Exception:
                # Tanner (9/28/23): not raising the exception here to avoid user-defined metadata issues stopping entire analyses
                logger.exception("Inserting user-defined metadata into DB failed")

            if use_existing_time_v_force:
                logger.info("Skipping step to write time force data for upload")
            else:
                try:
                    recording_df = first_recording.to_dataframe()
                    recording_df.to_parquet(parquet_path)

                    upload_file_to_s3(bucket=PULSE3D_UPLOADS_BUCKET, key=parquet_key, file=parquet_path)
                    logger.info(f"Uploaded time force data to {parquet_key}")
                except Exception:
                    logger.exception("Writing or uploading time force data failed")
                    raise

            try:
                peaks_valleys_dict = dict()
                if not interactive_analysis:
                    logger.info("Running peak_detector")
                    # remove raw data columns
                    columns = [c for c in recording_df.columns if "__raw" not in c]
                    # this is to handle analyses run before PR.to_dataframe() where time is in seconds
                    time = recording_df[columns[0]].tolist()

                    peak_detector_params = (
                        "relative_prominence_factor",
                        "noise_prominence_factor",
                        "height_factor",
                        "width_factors",
                        "start_time",
                        "end_time",
                        "max_frequency",
                        "valley_search_duration",
                        "upslope_duration",
                        "upslope_noise_allowance_duration",
                    )

                    peak_detector_args = {
                        param: val
                        for param in peak_detector_params
                        if (val := analysis_params.get(param)) is not None
                    }

                    peaks_valleys_for_df = dict()
                    for well in columns:
                        if not _is_valid_well_name(well):
                            continue

                        well_force = recording_df[well].dropna().tolist()
                        interpolated_well_data = np.row_stack([time[: len(well_force)], well_force])
                        # noise based peak finding requires times to be in seconds
                        interpolated_well_data[0] /= MICRO_TO_BASE_CONVERSION

                        try:
                            peaks, valleys = noise_based_peak_finding(
                                interpolated_well_data, **peak_detector_args
                            )
                        except (InvalidValleySearchDurationError, TooFewPeaksDetectedError):
                            peaks = []
                            valleys = []

                        # need to initialize a dict with these values and then create the DF otherwise values will be truncated
                        peaks_valleys_for_df[f"{well}__peaks"] = pd.Series(peaks)
                        peaks_valleys_for_df[f"{well}__valleys"] = pd.Series(valleys)

                        # write_xlsx takes in peaks_valleys: Dict[str, List[List[int]]]
                        peaks_valleys_dict[well] = [peaks, valleys]
                    # this df will be written to parquet and stored in s3, two columns for each well prefixed with well name
                    peaks_valleys_df = pd.DataFrame(peaks_valleys_for_df)
                else:
                    logger.info("Formatting peaks and valleys")
                    peaks_valleys_df = pd.read_parquet(pv_temp_path)

                    for well in first_recording:
                        well_name = well[WELL_NAME_UUID]

                        peaks = peaks_valleys_df[f"{well_name}__peaks"].dropna().tolist()
                        valleys = peaks_valleys_df[f"{well_name}__valleys"].dropna().tolist()

                        peaks_valleys_dict[well_name] = [[int(x) for x in pv] for pv in (peaks, valleys)]

                # set in analysis params to be passed to write_xlsx
                analysis_params["peaks_valleys"] = peaks_valleys_dict

            except Exception:
                logger.exception("Failed to get peaks and valleys for write_xlsx")
                raise

            if not interactive_analysis:
                try:
                    peaks_valleys_df.to_parquet(pv_temp_path)

                    upload_file_to_s3(bucket=PULSE3D_UPLOADS_BUCKET, key=pv_parquet_key, file=pv_temp_path)
                    logger.info(f"Uploaded peaks and valleys to {pv_parquet_key}")
                except Exception:
                    logger.exception("Writing or uploading peaks and valleys failed")
                    raise
            else:
                logger.info("Skipping the writing of peaks and valleys to parquet in S3")

            try:
                outfile = write_xlsx(first_recording, output_dir=tmpdir, **analysis_params)
                outfile_prefix = prefix.replace("uploads/", "analyzed/")
                outfile_key = f"{outfile_prefix}/{job_id}/{outfile}"
            except Exception:
                logger.exception("Writing xlsx output failed")
                raise

            try:
                analysis_params_updates = {}

                # well_groups may have been sent in a dashboard reanalysis or upload, don't override here
                if well_groups is None:
                    platemap_labels = dict()

                    for well_file in first_recording:
                        label = well_file[PLATEMAP_LABEL_UUID]

                        # only add to platemap_labels if label has been assigned
                        if label != NOT_APPLICABLE_LABEL:
                            # add label to dictionary if not already present
                            if label not in platemap_labels:
                                platemap_labels[label] = list()

                            platemap_labels[label].append(well_file[WELL_NAME_UUID])

                    # only change assignment if any groups were found, else it will be an empty dictionary
                    if platemap_labels:
                        # update new well groups
                        analysis_params_updates.update({"well_groups": platemap_labels})

                # if the data type is set in the recording metadata and no override was given, update the params
                if (
                    data_type_from_pr := first_recording.wells[0].get(str(DATA_TYPE_UUID))
                ) and not analysis_params.get("data_type"):
                    analysis_params_updates["data_type"] = data_type_from_pr

                if analysis_params_updates:
                    logger.info(f"Updating analysis params in job's metadata: {analysis_params_updates}")
                    # get the original params that aren't missing any plate_recordings_args or anything else
                    new_analysis_params = json.loads(item["meta"])["analysis_params"]
                    new_analysis_params |= analysis_params_updates
                    # add to job_metadata to get updated in jobs_result table
                    job_metadata |= {"analysis_params": new_analysis_params}
                else:
                    logger.info("No updates needed for analysis params in job's metadata")

            except Exception:
                logger.exception("Error updating analysis params")
                raise

            with open(outfile, "rb") as file:
                try:
                    contents = file.read()
                    md5 = hashlib.md5(contents).digest()
                    md5s = base64.b64encode(md5).decode()

                    s3_client.put_object(
                        Body=contents, Bucket=PULSE3D_UPLOADS_BUCKET, Key=outfile_key, ContentMD5=md5s
                    )

                    logger.info(f"Uploaded {outfile} to {PULSE3D_UPLOADS_BUCKET}/{outfile_key}")
                except Exception:
                    logger.exception("Upload failed")
                    raise

                try:
                    plate_barcode, stim_barcode, recording_length_ms = await insert_metadata_into_pg(
                        con,
                        first_recording,
                        upload_details["customer_id"],
                        upload_details["user_id"],
                        upload_id,
                        file,
                        outfile_key,
                        re_analysis,
                    )

                    job_metadata |= {
                        "plate_barcode": plate_barcode,
                        "stim_barcode": stim_barcode,
                        "recording_length_ms": recording_length_ms,
                    }

                    logger.info(f"Inserted {outfile} metadata into db for upload {upload_id}")
                except Exception:
                    logger.exception("Failed to insert metadata to db")
                    raise

    except Exception as e:
        job_metadata["error"] = f"{str(e)}"
        result = "error"
    else:
        logger.info("Job complete")
        result = "finished"

    # clear bound variables (IDs) for this job to reset for next job
    clear_contextvars()

    return result, job_metadata, outfile_key


async def main():
    try:
        logger.info(f"Worker v{PULSE3D_VERSION} started")

        DB_PASS = os.getenv("POSTGRES_PASSWORD")
        DB_USER = os.getenv("POSTGRES_USER", default="curibio_jobs")
        DB_HOST = os.getenv("POSTGRES_SERVER", default="psql-rds.default")
        DB_NAME = os.getenv("POSTGRES_DB", default="curibio")

        dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"

        async with asyncpg.create_pool(dsn=dsn) as pool:
            async with pool.acquire() as con, pool.acquire() as con_to_update_job_result:
                while True:
                    try:
                        logger.info("Pulling job from queue")
                        await process(con=con, con_to_update_job_result=con_to_update_job_result)
                    except EmptyQueue as e:
                        logger.info(f"No jobs in queue: {e}")
                        return
                    except Exception:
                        logger.exception("Processing queue item failed")
                        return
    finally:
        logger.info(f"Worker v{PULSE3D_VERSION} terminating")


if __name__ == "__main__":
    asyncio.run(main())
