import asyncio
import base64
import hashlib
import json
import logging
import os
import pkg_resources
import sys
import tempfile

import asyncpg
import boto3
import pandas as pd
import numpy as np

from pulse3D.constants import MICRO_TO_BASE_CONVERSION
from pulse3D.constants import WELL_NAME_UUID
from pulse3D.constants import PLATEMAP_LABEL_UUID
from pulse3D.constants import NOT_APPLICABLE_LABEL
from pulse3D.excel_writer import write_xlsx
from pulse3D.peak_detection import peak_detector
from pulse3D.plate_recording import PlateRecording

from jobs import get_item, EmptyQueue
from utils.s3 import upload_file_to_s3
from lib.db import insert_metadata_into_pg, PULSE3D_UPLOADS_BUCKET

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

PULSE3D_VERSION = pkg_resources.get_distribution("pulse3D").version


def _load_from_dir(recording_dir, plate_recording_args):
    recordings = list(PlateRecording.from_directory(recording_dir, **plate_recording_args))
    logger.info(f"{len(recordings)} recording(s) found")
    return recordings


# TODO move this to core lib
def _is_valid_well_name(well_name):
    return (
        isinstance(well_name, str)
        and len(well_name) == 2
        and well_name[0] in ("A", "B", "C", "D")
        and well_name[1] in [str(n) for n in range(1, 7)]
    )


@get_item(queue=f"pulse3d-v{PULSE3D_VERSION}")
async def process(con, item):
    logger.info(f"Processing item: {item}")
    s3_client = boto3.client("s3")
    job_metadata = {"processed_by": PULSE3D_VERSION}
    outfile_key = None

    try:
        try:
            job_id = item["id"]
            upload_id = item["upload_id"]

            logger.info(f"Retrieving user ID and metadata for upload with ID: {upload_id}")

            query = (
                "SELECT users.customer_id, up.user_id, up.prefix, up.filename "
                "FROM uploads AS up JOIN users ON up.user_id = users.id "
                "WHERE up.id=$1"
            )

            upload_details = await con.fetchrow(query, upload_id)

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

        except Exception as e:
            logger.exception(f"Fetching upload details failed: {e}")
            raise

        with tempfile.TemporaryDirectory(dir="/tmp") as tmpdir:
            logger.info(f"Downloading {PULSE3D_UPLOADS_BUCKET}/{key} to {tmpdir}/{analysis_filename}")
            # adding prefix here representing the version of pulse3D used
            parquet_filename = f"{os.path.splitext(upload_filename)[0]}.parquet"
            parquet_key = f"{prefix}/time_force_data/{PULSE3D_VERSION}/{parquet_filename}"
            parquet_path = os.path.join(tmpdir, parquet_filename)
            # set variables for where peaks and valleys should be or where it will go in s3
            pv_parquet_key = f"{prefix}/{job_id}/peaks_valleys.parquet"
            pv_temp_path = os.path.join(tmpdir, "peaks_valleys.parquet")

            try:
                s3_client.download_file(PULSE3D_UPLOADS_BUCKET, key, f"{tmpdir}/{analysis_filename}")
            except Exception as e:
                logger.exception(f"Failed to download recording zip file: {e}")
                raise

            try:
                # attempt to download parquet file if recording has already been analyzed
                logger.info("Checking if time force data exists in s3")

                s3_client.download_file(PULSE3D_UPLOADS_BUCKET, parquet_key, parquet_path)
                re_analysis = True

                logger.info(f"Successfully downloaded {parquet_filename} to {parquet_path}")
            except Exception:  # continue with analysis even if original force data is not found
                logger.error(f"No existing data found for recording {parquet_filename}")
                re_analysis = False

            try:
                # attempt to download peaks and valleys from s3, will only be the case for interactive analysis jobs
                logger.info("Checking if peaks and valleys exist in s3")

                s3_client.download_file(PULSE3D_UPLOADS_BUCKET, pv_parquet_key, pv_temp_path)
                interactive_analysis = True

                logger.info(f"Successfully downloaded peaks and valleys to {pv_temp_path}")
            except Exception:  # continue with analysis even if original force data is not found
                logger.error("No existing peaks and valleys found for recording")
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
                    logger.info(f"Loading previous time force data from {parquet_filename}")
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

            except Exception as e:
                logger.exception(f"PlateRecording failed: {e}")
                raise

            if use_existing_time_v_force:
                logger.info("Skipping step to write time force data for upload")
            else:
                try:
                    logger.info("Writing time force data to parquet file for new upload")
                    recording_df = first_recording.to_dataframe()
                    recording_df.to_parquet(parquet_path)

                    upload_file_to_s3(bucket=PULSE3D_UPLOADS_BUCKET, key=parquet_key, file=parquet_path)
                    logger.info(f"Uploaded time force data to {parquet_key}")
                except Exception as e:
                    logger.exception(f"Writing or uploading time force data failed: {e}")
                    raise

            try:
                peaks_valleys_dict = dict()
                if not interactive_analysis:
                    logger.info("Running peak_detector on recording for export to parquet")
                    # remove raw data columns
                    columns = [c for c in recording_df.columns if "__raw" not in c]
                    # this is to handle analyses run before PR.to_dataframe() where time is in seconds
                    time = recording_df[columns[0]].tolist()
                    peak_detector_args = {
                        param: val
                        for param in ("prominence_factors", "width_factors", "start_time", "end_time")
                        if (val := analysis_params.get(param)) is not None
                    }
                    for param in ("start_time", "end_time"):
                        if param in peak_detector_args:
                            # these values are in seconds but need to be converted to µs for peak_detector
                            peak_detector_args[param] *= MICRO_TO_BASE_CONVERSION

                    peaks_valleys_for_df = dict()
                    for well in columns:
                        if not _is_valid_well_name(well):
                            continue

                        logger.info(f"Finding peaks and valleys for well {well}")
                        well_force = recording_df[well].dropna().tolist()
                        interpolated_well_data = np.row_stack([time[: len(well_force)], well_force])
                        peaks, valleys = peak_detector(interpolated_well_data, **peak_detector_args)

                        # need to initialize a dict with these values and then create the DF otherwise values will be truncated
                        peaks_valleys_for_df[f"{well}__peaks"] = pd.Series(peaks)
                        peaks_valleys_for_df[f"{well}__valleys"] = pd.Series(valleys)

                        # write_xlsx takes in peaks_valleys: Dict[str, List[List[int]]]
                        peaks_valleys_dict[well] = [peaks, valleys]
                    # this df will be written to parquet and stored in s3, two columns for each well prefixed with well name
                    peaks_valleys_df = pd.DataFrame(peaks_valleys_for_df)
                else:
                    logger.info("Formatting peaks and valleys from parquet file for write_xlsx")
                    peaks_valleys_df = pd.read_parquet(pv_temp_path)

                    for well in first_recording:
                        well_name = well[WELL_NAME_UUID]

                        peaks = peaks_valleys_df[f"{well_name}__peaks"].dropna().tolist()
                        valleys = peaks_valleys_df[f"{well_name}__valleys"].dropna().tolist()

                        peaks_valleys_dict[well_name] = [[int(x) for x in peaks], [int(x) for x in valleys]]

                # set in analysis params to be passed to write_xlsx
                analysis_params["peaks_valleys"] = peaks_valleys_dict

            except Exception as e:
                logger.exception(f"Failed to get peaks and valleys for write_xlsx: {e}")
                raise

            if not interactive_analysis:
                try:
                    logger.info(f"Writing peaks and valleys to parquet file for job: {job_id}")
                    peaks_valleys_df.to_parquet(pv_temp_path)

                    upload_file_to_s3(bucket=PULSE3D_UPLOADS_BUCKET, key=pv_parquet_key, file=pv_temp_path)
                    logger.info(f"Uploaded peaks and valleys to {pv_parquet_key}")
                except Exception as e:
                    logger.exception(f"Writing or uploading peaks and valleys failed: {e}")
                    raise
            else:
                logger.info("Skipping the writing of peaks and valleys to parquet in S3")

            try:
                outfile = write_xlsx(first_recording, **analysis_params)
                outfile_prefix = prefix.replace("uploads/", "analyzed/")
                outfile_key = f"{outfile_prefix}/{job_id}/{outfile}"
            except Exception as e:
                logger.exception(f"Writing xlsx output failed: {e}")
                raise

            try:
                logger.info("Checking if well groups need to be updated in job's metadata")
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
                        # get the original params that aren't missing any plate_recordings_args
                        updated_analysis_params = json.loads(item["meta"])["analysis_params"]
                        # update new well groups
                        updated_analysis_params.update({"well_groups": platemap_labels})
                        # add to job_metadata to get updated in jobs_result table
                        job_metadata |= {"analysis_params": updated_analysis_params}

            except Exception as e:
                logger.exception(f"Error updating well groups: {e}")
                raise

            with open(outfile, "rb") as file:
                try:
                    logger.info(f"Uploading {outfile} to {PULSE3D_UPLOADS_BUCKET}/{outfile_key}")

                    contents = file.read()
                    md5 = hashlib.md5(contents).digest()
                    md5s = base64.b64encode(md5).decode()

                    s3_client.put_object(
                        Body=contents, Bucket=PULSE3D_UPLOADS_BUCKET, Key=outfile_key, ContentMD5=md5s
                    )
                except Exception as e:
                    logger.exception(f"Upload failed: {e}")
                    raise

                try:
                    logger.info(f"Inserting {outfile} metadata into db for upload {upload_id}")
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
                except Exception as e:
                    logger.exception(f"Failed to insert metadata to db for upload {upload_id}: {e}")
                    raise

    except Exception as e:
        job_metadata["error"] = f"{str(e)}: {item}"
        result = "error"
    else:
        logger.info(f"Job complete for upload {upload_id}")
        result = "finished"

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
            async with pool.acquire() as con, pool.acquire() as con_to_set_job_running:
                while True:
                    try:
                        logger.info("Pulling job from queue")
                        await process(con=con, con_to_set_job_running=con_to_set_job_running)
                    except EmptyQueue as e:
                        logger.info(f"No jobs in queue: {e}")
                        return
                    except Exception as e:
                        logger.exception(f"Processing queue item failed: {repr(e)}")
                        return
    finally:
        logger.info(f"Worker v{PULSE3D_VERSION} terminating")


if __name__ == "__main__":
    asyncio.run(main())
