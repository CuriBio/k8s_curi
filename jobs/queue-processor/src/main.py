import asyncio
import asyncpg
from kubernetes import config, client as kclient
import json
import os
import logging
import sys
import math
from time import sleep

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

SECONDS_TO_POLL_DB = int(os.getenv("SECONDS_TO_POLL_DB"))
ECR_REPO = os.getenv("ECR_REPO")
MAX_JOBS_PER_WORKER = int(os.getenv("MAX_JOBS_PER_WORKER", default=5))
QUEUE = os.getenv("QUEUE")
DB_PASS = os.getenv("POSTGRES_PASSWORD")
DB_USER = os.getenv("POSTGRES_USER", default="curibio_operators_ro")
DB_HOST = os.getenv("POSTGRES_SERVER", default="psql-rds.default")
DB_NAME = os.getenv("POSTGRES_DB", default="curibio")


async def create_job(version: str, num_of_workers: int):
    # load kube config
    config.load_incluster_config()

    for count in range(1, num_of_workers + 1):
        # names can only be alphanumeric and '-' so replacing '.' with '-'
        # Adding count may potentially not work as expected if workers keep getting kicked off in another loop
        formatted_name = f"{QUEUE}-worker-v{'-'.join(version.split('.'))}--{count}"
        logger.info(f"Starting {formatted_name}")
        complete_ecr_repo = f"{ECR_REPO}:{version}-test"
        POSTGRES_PASSWORD = kclient.V1EnvVar(
            name="POSTGRES_PASSWORD",
            value_from=kclient.V1EnvVarSource(
                secret_key_ref=kclient.V1SecretKeySelector(name="curibio-jobs-creds", key="curibio_jobs")
            ),
        )

        # Create container
        container = kclient.V1Container(
            name=formatted_name,
            image=complete_ecr_repo,
            env=[POSTGRES_PASSWORD],
        )
        # Create job spec with container
        spec = kclient.V1JobSpec(
            template={"spec": {"containers": [container], "restartPolicy": "Never"}},
            backoff_limit=2,
            ttl_seconds_after_finished=60,
        )
        # Instantiate the job object
        job = kclient.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=kclient.V1ObjectMeta(name=formatted_name),
            spec=spec,
        )
        api = kclient.BatchV1Api()
        api.create_namespaced_job(namespace="pulse3d", body=job)


async def get_next_queue_item():
    dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"

    async with asyncpg.create_pool(dsn=dsn) as pool:
        async with pool.acquire() as con:
            records = await con.fetch(
                "SELECT meta->'version' AS version, COUNT(*) FROM jobs_queue WHERE queue LIKE $1 GROUP BY version",
                f"%{QUEUE}%",  # TODO change this to {queue}%
            )

            for record in records:
                version = json.loads(record["version"])
                # currently set one worker per 5 queue items
                # TODO make count value an env variable to make it easier to change
                num_of_workers = math.ceil(record["count"] / MAX_JOBS_PER_WORKER)
                logger.info(f"Starting {num_of_workers} worker(s) for {QUEUE}:{version}")

                await create_job(version, num_of_workers)


if __name__ == "__main__":
    try:
        while True:
            logger.info(f"Checking {QUEUE} queue for new items")
            asyncio.run(get_next_queue_item())
            sleep(SECONDS_TO_POLL_DB)
    except Exception as e:
        logger.exception(f"EXCEPTION OCCURRED IN QUEUE PROCESSOR: {e}")
