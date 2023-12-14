import asyncio
import asyncpg
from kubernetes import config, client as kclient
import json
import os
import random
import structlog
from structlog.contextvars import bind_contextvars, bound_contextvars, merge_contextvars
from time import sleep

structlog.configure(
    processors=[
        merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M.%S"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.getLogger()

SECONDS_TO_POLL_DB = int(os.getenv("SECONDS_TO_POLL_DB"))
ECR_REPO = os.getenv("ECR_REPO")
MAX_NUM_OF_WORKERS = int(os.getenv("MAX_NUM_OF_WORKERS", default=5))
QUEUE = os.getenv("QUEUE")
DB_PASS = os.getenv("POSTGRES_PASSWORD")
DB_USER = os.getenv("POSTGRES_USER")
DB_HOST = os.getenv("POSTGRES_SERVER", default="psql-rds.default")
DB_NAME = os.getenv("POSTGRES_DB", default="curibio")

MANTARRAY_LOGS_BUCKET = kclient.V1EnvVar(
    name="MANTARRAY_LOGS_BUCKET_ENV", value=os.getenv("mantarray_logs_bucket")
)
PULSE3D_UPLOADS_BUCKET = kclient.V1EnvVar(
    name="UPLOADS_BUCKET_ENV", value=os.getenv("pulse3d_uploads_bucket")
)


async def create_job(version: str, num_of_workers: int):
    # load kube config
    config.load_incluster_config()
    job_api = kclient.BatchV1Api()
    pod_api = kclient.CoreV1Api()

    # get pod list to get uid to use in owner_reference when spinning up new jobs
    # the pod needed is the pod this code is being executed in
    qp_pods_list = pod_api.list_namespaced_pod(namespace="pulse3d", label_selector=f"app={QUEUE}_qp")
    # get existing jobs to prevent starting a job with the same count suffix
    # make sure to only get jobs of specific version
    running_workers_list = job_api.list_namespaced_job(QUEUE, label_selector=f"job_version={version}")
    num_of_active_workers = len(running_workers_list.items)

    logger.info(f"Checking for active {version} workers: {num_of_active_workers} found.")
    logger.info(f"Starting {num_of_workers - num_of_active_workers} worker(s) for {QUEUE}:{version}.")

    for count in range(num_of_active_workers + 1, num_of_workers + 1):
        worker_id = hex(random.getrandbits(40))[2:]
        # names can only be alphanumeric and '-' so replacing '.' with '-'
        # Cannot start jobs with the same name so count starting at 1+existing number of jobs running in namespace with version
        formatted_name = f"{QUEUE}-worker-v{'-'.join(version.split('.'))}--{count}--{worker_id}"
        logger.info(f"Starting {formatted_name}.")
        complete_ecr_repo = f"{ECR_REPO}:{version}"

        POSTGRES_PASSWORD = kclient.V1EnvVar(
            name="POSTGRES_PASSWORD",
            value_from=kclient.V1EnvVarSource(
                secret_key_ref=kclient.V1SecretKeySelector(name="curibio-jobs-creds", key="curibio_jobs")
            ),
        )
        resources = kclient.V1ResourceRequirements(requests={"memory": "1000Mi"})
        # Create container
        container = kclient.V1Container(
            name=formatted_name,
            image=complete_ecr_repo,
            env=[POSTGRES_PASSWORD, PULSE3D_UPLOADS_BUCKET, MANTARRAY_LOGS_BUCKET],
            image_pull_policy="Always",
            resources=resources,
        )
        # Create job spec with container
        spec = kclient.V1JobSpec(
            template={
                "spec": {
                    "containers": [container],
                    "restartPolicy": "Never",
                    "nodeSelector": {"group": "workers"},
                }
            },
            backoff_limit=2,
            ttl_seconds_after_finished=60,
        )
        # Instantiate the job object
        job = kclient.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=kclient.V1ObjectMeta(
                name=formatted_name,
                labels={"job_version": version},
                owner_references=[
                    kclient.V1OwnerReference(
                        api_version="v1",
                        controller=True,
                        kind="Pod",
                        uid=qp_pods_list.items[0].metadata.uid,
                        name=qp_pods_list.items[0].metadata.name,
                    )
                ],
            ),
            spec=spec,
        )

        job_api.create_namespaced_job(namespace="pulse3d", body=job)


async def get_next_queue_item():
    dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"

    async with asyncpg.create_pool(dsn=dsn) as pool:
        async with pool.acquire() as con:
            records = await con.fetch(
                "SELECT meta->'version' AS version, COUNT(*) FROM jobs_queue WHERE queue LIKE $1 GROUP BY version",
                f"{QUEUE}%",
            )

            if not records:
                logger.info("Queue is empty, nothing to process.")

            for record in records:
                version = json.loads(record["version"])
                with bound_contextvars(version=version):
                    logger.info(f"Found {record['count']} item(s) for {version}.")
                    # spin up max 5 workers, one per first five jobs in queue
                    num_of_workers = min(record["count"], MAX_NUM_OF_WORKERS)

                    await create_job(version, num_of_workers)


if __name__ == "__main__":
    bind_contextvars(queue=QUEUE)

    while True:
        try:
            logger.info("Checking queue for new items")
            asyncio.run(get_next_queue_item())
            sleep(SECONDS_TO_POLL_DB)
        except Exception as e:
            logger.exception(f"EXCEPTION OCCURRED IN QUEUE PROCESSOR: {e}")
