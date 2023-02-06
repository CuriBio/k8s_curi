import asyncio
import asyncpg
from kubernetes import config, client as kclient
import json
import os


async def create_job(version: str, db_pass: str):
    # load kube config
    config.load_incluster_config()
    version = json.loads(version)
    # names can only be alphanumeric and '-' so replacing '.' with '-'
    formatted_name = f"pulse3d-worker-v{'-'.join(version.split('.'))}"
    POSTGRES_PASSWORD = kclient.V1EnvVar(name="POSTGRES_PASSWORD", value=db_pass)

    base_repo = os.getenv("ECR_REPO")
    ECR_REPO = f"{base_repo}:test-{version}"

    # Create container
    container = kclient.V1Container(
        name=formatted_name,
        image=ECR_REPO,
        env=[POSTGRES_PASSWORD],
    )

    spec = kclient.V1JobSpec(
        template={"spec": {"containers": [container], "restartPolicy": "Never"}},
        backoff_limit=2,
        # ttl_seconds_after_finished=0,
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

    DB_PASS = os.getenv("POSTGRES_PASSWORD")
    QUEUE = os.getenv("QUEUE")

    dsn = f"postgresql://curibio_operators_ro:{DB_PASS}@psql-rds.default:5432/curibio"

    async with asyncpg.create_pool(dsn=dsn) as pool:
        async with pool.acquire() as con:
            records = await con.fetchrow(
                "SELECT meta->'version' AS version FROM jobs_queue WHERE queue LIKE $1 ORDER BY priority DESC, created_at ASC",
                f"%{QUEUE}%",  # todo change this to {queue}%
            )

            for version in set(records):
                await create_job(version, DB_PASS)


if __name__ == "__main__":
    # try:
    asyncio.run(get_next_queue_item())
    # except Exception as e:
    #     print(f"EXCEPTION OCCURRED: {e}")
