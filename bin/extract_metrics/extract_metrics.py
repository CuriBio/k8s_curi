"""
Check uploads table in DB for rows which do not have metadata set. Use pulse3D to extract the metadata from
the recording files and update the rows.
"""

import asyncio
import datetime
import json
import logging
import os
import sys
import tempfile
from typing import Any
from zipfile import ZipFile

import asyncpg
import boto3
import polars as pl
from pulse3D import metrics
from pulse3D.data_loader.utils import get_metadata_cls
from pulse3D.peak_finding import LoadedDataWithFeatures
from pulse3D.pre_analysis import sort_wells_in_df, apply_window_to_df
from utils.s3 import upload_file_to_s3

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
                    res = await process_job(con, job_info)
                    job_counts[res] += 1
    finally:
        logger.info(f"result: {job_counts}")
        logger.info("DONE")


def _create_file_info(
    base_dir: str, upload_prefix: str, job_id: str, p3d_analysis_version: str
) -> dict[str, Any]:
    pre_process_dir = os.path.join(base_dir, "pre-process")
    os.mkdir(pre_process_dir)
    pre_process_filename = "pre-process.zip"
    pre_process_file_s3_key = f"{upload_prefix}/pre-process/{p3d_analysis_version}/{pre_process_filename}"
    pre_process_file_path = os.path.join(pre_process_dir, pre_process_filename)

    pre_analysis_dir = os.path.join(base_dir, "pre-analysis")
    os.mkdir(pre_analysis_dir)
    pre_analysis_filename = "pre-analysis.zip"
    pre_analysis_file_s3_key = f"{upload_prefix}/{job_id}/{pre_analysis_filename}"
    pre_analysis_file_path = os.path.join(pre_analysis_dir, pre_analysis_filename)

    peak_finding_dir = os.path.join(base_dir, "peak_finding")
    os.mkdir(peak_finding_dir)
    peak_finding_filename = "peaks_valleys.parquet"
    peak_finding_s3_key = f"{upload_prefix}/{job_id}/{peak_finding_filename}"
    peak_finding_file_path = os.path.join(base_dir, peak_finding_filename)

    metrics_dir = os.path.join(base_dir, "metrics")
    os.mkdir(metrics_dir)
    per_twitch_metrics_filename = "per_twitch_metrics.parquet"
    per_twitch_metrics_s3_key = f"{upload_prefix}/{job_id}/{per_twitch_metrics_filename}"
    per_twitch_metrics_file_path = os.path.join(base_dir, per_twitch_metrics_filename)
    aggregate_metrics_filename = "aggregate_metrics.parquet"
    aggregate_metrics_s3_key = f"{upload_prefix}/{job_id}/{aggregate_metrics_filename}"
    aggregate_metrics_file_path = os.path.join(base_dir, aggregate_metrics_filename)

    return {
        "zip_contents": {
            "tissue": "tissue_waveforms.parquet",
            "stim": "stim_waveforms.parquet",
            "metadata": "metadata.json",
        },
        "pre_process": {
            "dir": pre_process_dir,
            "filename": pre_process_filename,
            "file_path": pre_process_file_path,
            "s3_key": pre_process_file_s3_key,
        },
        "pre_analysis": {
            "dir": pre_analysis_dir,
            "filename": pre_analysis_filename,
            "file_path": pre_analysis_file_path,
            "s3_key": pre_analysis_file_s3_key,
        },
        "peak_finding": {
            "dir": peak_finding_dir,
            "filename": peak_finding_filename,
            "file_path": peak_finding_file_path,
            "s3_key": peak_finding_s3_key,
        },
        "per_twitch_metrics": {
            "dir": metrics_dir,
            "filename": per_twitch_metrics_filename,
            "file_path": per_twitch_metrics_file_path,
            "s3_key": per_twitch_metrics_s3_key,
        },
        "aggregate_metrics": {
            "dir": metrics_dir,
            "filename": aggregate_metrics_filename,
            "file_path": aggregate_metrics_file_path,
            "s3_key": aggregate_metrics_s3_key,
        },
    }


async def process_job(con, job_info) -> str:
    job_id = job_info["job_id"]
    try:
        logger.info("getting S3 prefix")
        try:
            prefix = await con.fetchval("select prefix from uploads where id=$1", job_info["upload_id"])
        except Exception:
            logger.error("failed getting prefix")
            raise

        logger.info("loading analysis params")
        try:
            metadata = json.loads(job_info["meta"])
            p3d_analysis_version = metadata["version"]
            analysis_params = {k: v for k, v in metadata["analysis_params"].items() if v is not None}
            post_process_params = {
                k: v
                for k, v in analysis_params.items()
                if k in ["normalization_method", "start_time", "end_time"]
            }
        except Exception:
            logger.error("failed getting analysis_params")
            raise

        with tempfile.TemporaryDirectory() as tmpdir:
            file_info = _create_file_info(tmpdir, prefix, str(job_id), p3d_analysis_version)

            logger.info("checking for existing metric output in S3")
            try:
                s3_client.head_object(
                    Bucket=PULSE3D_UPLOADS_BUCKET, Key=file_info["aggregate_metrics"]["s3_key"]
                )
            except Exception:
                logger.info("existing metrics not found, continuing")
            else:
                logger.info("existing metrics found, skipping")
                return "skipped"

            logger.info("downloading pre-analysis data")
            try:
                s3_client.download_file(
                    PULSE3D_UPLOADS_BUCKET,
                    file_info["pre_analysis"]["s3_key"],
                    file_info["pre_analysis"]["file_path"],
                )
                logger.info(
                    f"downloaded existing pre-analysis data to {file_info['pre_analysis']['file_path']}"
                )
            except Exception:
                logger.error("failed downloading pre-analysis data")
                raise

            logger.info("loading pre-analysis parquet")
            try:
                with ZipFile(file_info["pre_analysis"]["file_path"]) as z:
                    z.extractall(file_info["pre_analysis"]["dir"])

                pre_analysis_tissue_waveforms = pl.read_parquet(
                    os.path.join(file_info["pre_analysis"]["dir"], file_info["zip_contents"]["tissue"])
                )
                metadata_dict = json.load(
                    open(
                        os.path.join(file_info["pre_analysis"]["dir"], file_info["zip_contents"]["metadata"])
                    )
                )
                loaded_metadata = get_metadata_cls(metadata_dict)
            except Exception:
                logger.error("failed loading pre-analysis parquet")
                raise

            logger.info("downloading peak finding data")
            try:
                s3_client.download_file(
                    PULSE3D_UPLOADS_BUCKET,
                    file_info["peak_finding"]["s3_key"],
                    file_info["peak_finding"]["file_path"],
                )
                logger.info("downloaded peak finding data")
            except:
                logger.error("failed downloading peak finding data")
                raise

            logger.info("loading peak finding data")
            try:
                features_df = pl.read_parquet(file_info["peak_finding"]["file_path"])

                features_df = sort_wells_in_df(features_df, loaded_metadata.total_well_count)
                features_df = apply_window_to_df(
                    features_df, df_name_to_log="features", **post_process_params
                )

                data_with_features = LoadedDataWithFeatures(
                    metadata=loaded_metadata,
                    tissue_waveforms=pre_analysis_tissue_waveforms,
                    stim_waveforms=None,
                    tissue_features=features_df,
                )
            except:
                logger.error("failed loading peak finding data")
                raise

            logger.info("creating metrics")
            try:
                metrics_args = {
                    arg_name: val
                    for arg_name, orig_name in (
                        ("widths", "twitch_widths"),
                        ("baseline_widths", "baseline_widths_to_use"),
                        ("well_groups", "well_groups"),
                    )
                    if (val := analysis_params.get(orig_name)) is not None
                }
                metrics_output = metrics.run(data_with_features, **metrics_args)
                logger.info("created metrics")
            except Exception:
                logger.error("failed creating metrics")
                raise

            if DRY_RUN:
                return "success"

            # Upload metrics
            logger.info("uploading per-twitch metrics")
            try:
                metrics_output.per_twitch_metrics.write_parquet(file_info["per_twitch_metrics"]["file_path"])
                upload_file_to_s3(
                    bucket=PULSE3D_UPLOADS_BUCKET,
                    key=file_info["per_twitch_metrics"]["s3_key"],
                    file=file_info["per_twitch_metrics"]["file_path"],
                )
                logger.info(
                    f"uploaded per-twitch metrics to {PULSE3D_UPLOADS_BUCKET}/{file_info['per_twitch_metrics']['s3_key']}"
                )
            except Exception:
                logger.error("upload of per-twitch metrics failed")
                raise
            logger.info("uploading aggregate metrics")
            try:
                metrics_output.aggregate_metrics.write_parquet(file_info["aggregate_metrics"]["file_path"])
                upload_file_to_s3(
                    bucket=PULSE3D_UPLOADS_BUCKET,
                    key=file_info["aggregate_metrics"]["s3_key"],
                    file=file_info["aggregate_metrics"]["file_path"],
                )
                logger.info(
                    f"uploaded aggregate metrics to {PULSE3D_UPLOADS_BUCKET}/{file_info['aggregate_metrics']['s3_key']}"
                )
            except Exception:
                logger.error("upload of aggregate metrics failed")
                raise
        return "success"
    except KeyboardInterrupt:
        raise
    except:
        logger.exception(f"failed processing job: {job_id}")
        return "failed"


if __name__ == "__main__":
    asyncio.run(main())
