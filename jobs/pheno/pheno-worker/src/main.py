import sys
import tempfile
import logging
import json
import os
from time import sleep  # TODO set up while loop to check for new queued entry

from psycopg2 import connect

from lib.constants import SELECT_QUERY
from lib.constants import UPDATE_QUERY
from lib.constants import PHENO_BUCKET

from lib.start_training import start_training
from lib.start_classification import start_classification
from lib.utils import get_db_params
from lib.utils import upload_logfile_to_s3


root = logging.getLogger()
if root.handlers:
    for handler in root.handlers:
        root.removeHandler(handler)

logger = logging.getLogger(__name__)

# ------------------------------------------ #


def handler():
    # set up logging for job
    tmp_dir = tempfile.TemporaryDirectory()
    LOG_FILENAME = os.path.join(tmp_dir.name, "tmp_logfile.log")

    log_handlers = list()
    log_handlers.append(logging.FileHandler(LOG_FILENAME))
    log_handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s UTC] %(name)s-{%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
        handlers=log_handlers,
    )

    try:
        params = get_db_params()
        with connect(**params) as conn:
            with conn.cursor() as cur:
                # query for rows in task_queue, limit 1
                cur.execute(SELECT_QUERY)
                row = cur.fetchone()
                logger.info(f"Selected row: {row}")

                if row != None:
                    # execute whatever app specic
                    job_type = row[3]  # will be an integer that we decide on
                    job_metadata = json.loads(row[5])
                    if job_type == 0:
                        job_status = start_training(job_metadata, LOG_FILENAME)
                        job_metadata = {"type": "training", "metadata": job_metadata}
                    elif job_type == 1:
                        job_status = start_classification(job_metadata, LOG_FILENAME)
                        job_metadata = {"type": "classification", "metadata": job_metadata}

                    # update affected rows
                    job_id = row[0]
                    cur.execute(UPDATE_QUERY, (job_status, job_id))
                    logger.info(f"Updated job_queue where id={job_id} with status: {job_status}")

            # commit changes to database
            conn.commit()
    except Exception as e:
        logger.error(f"Error in transaction: {e}")
        if conn:
            conn.rollback()
            logger.error("Rolling back to previous state.")

    finally:
        # upload log file
        upload_logfile_to_s3(PHENO_BUCKET, LOG_FILENAME, job_metadata, logger)
        # closing database connection
        tmp_dir.cleanup()
        logger.info("Performing final cleanup before closing \n")


# ------------------------------------------ #

if __name__ == "__main__":
    handler()
