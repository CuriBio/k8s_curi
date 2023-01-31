# import kopf
# import kubernetes
# import yaml
import asyncio
import asyncpg
import json
from kubernetes import config, client as kclient

# import boto3
# import os

# JOB_NAME = "test-pulse3d-worker"


# def create_job_object():
#     # Configureate Pod template container
#     container = kubernetes.client.V1Container(
#         name="pi", image="perl", command=["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
#     )

#     # Create and configure a spec section
#     template = kubernetes.client.V1PodTemplateSpec(
#         metadata=kubernetes.client.V1ObjectMeta(labels={"app": "pi"}),
#         spec=kubernetes.client.V1PodSpec(restart_policy="Never", containers=[container]),
#     )

#     # Create the specification of deployment
#     spec = kubernetes.client.V1JobSpec(template=template, backoff_limit=4)

#     # Instantiate the job object
#     job = kubernetes.client.V1Job(
#         api_version="batch/v1", kind="Job", metadata=kubernetes.client.V1ObjectMeta(name=JOB_NAME), spec=spec
#     )

#     return job


# @kopf.on.create("test", "v1", "job_runner")
# async def create_fn(body, spec, **kwargs):

#     # DB_PASS = os.getenv("POSTGRES_PASSWORD")
#     # DB_USER = os.getenv("POSTGRES_USER", default="curibio_jobs")
#     # DB_HOST = os.getenv("POSTGRES_SERVER", default="psql-rds.default")
#     # DB_NAME = os.getenv("POSTGRES_DB", default="curibio")
#     # dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
#     dsn = "postgresql://root:HjnlH9RaeTt7uRuF7Uwco6BX4l0jgp39@localhost:5432/curibio"
#     async with asyncpg.create_pool(dsn=dsn) as pool:
#         async with pool.acquire() as con:
#             async with con.transaction():
#                 query = (
#                     "SELECT meta FROM jobs_queue "
#                     "WHERE id = (SELECT id FROM jobs_queue WHERE queue=$1 ORDER BY priority DESC, created_at ASC FOR UPDATE SKIP LOCKED LIMIT 1)"
#                 )

#                 item = await con.fetchrow(query)
#                 if not item:
#                     raise EmptyQueue(queue)

#     # Get info from Database object
#     name = body["metadata"]["name"]
#     namespace = body["metadata"]["namespace"]
#     # type = spec['type']

#     # Make sure type is provided
#     # if not type:
#     #     raise kopf.HandlerFatalError(f"Type must be set. Got {type}.")

#     # Pod template
#     pod = {"apiVersion": "v1", "metadata": {"name": name, "labels": {"app": "db"}}}

#     # Job template
#     job = create_job_object()

#     # # Service template
#     # svc = {'apiVersion': 'v1', 'metadata': {'name' : name}, 'spec': { 'selector': {'app': 'db'}, 'type': 'NodePort'}}

#     # if type == 'mysql':
#     #   image = 'mysql:8.0'
#     #   port = 3306
#     #   pod['spec'] = { 'containers': [ { 'image': image, 'name': type, 'env': [ { 'name': 'MYSQL_ROOT_PASSWORD', 'value': 'my_passwd' } ] } ]}
#     #   svc['spec']['ports'] = [{ 'port': port, 'targetPort': port}]

#     kopf.adopt(job, owner=body)

#     # Object used to communicate with the API Server
#     # api = kubernetes.client.CoreV1Api()
#     api = kubernetes.client.BatchV1Api()

#     # Create Pod
#     obj = api.create_namespaced_job(body=job, namespace=namespace)
#     print(f"Job {obj.metadata.name} created")

#     # Create Service
#     # obj = api.create_namespaced_service(namespace, svc)
#     # print(f"NodePort Service {obj.metadata.name} created, exposing on port {obj.spec.ports[0].node_port}")

#     # Update status
#     msg = f"Pod and Service created by Database {name}"
#     return {"message": msg}


# @kopf.on.delete("test", "v1", "job_runner")
# def delete(body, **kwargs):
#     msg = f"Database {body['metadata']['name']} and its Pod / Service children deleted"
#     return {"message": msg}


async def create_job(version: str, queue: str):
    config.load_kube_config()  # TODO remove
    v1 = kclient.CoreV1Api()

    # queue_env = kclient.V1EnvVar(name="QUEUE", value=f"{}")

    # container = kclient.V1Container(
    #     name="queue-processor", image=ECR_REPO, command=["python", "main.py"], env=[queue_env]
    # )

    # # Create and configure a spec section
    # body = kclient.V1JobTemplateSpec(
    #     metadata=kclient.V1ObjectMeta(name=f"{queue}-queue-processor", labels={"app": "queue_processor"}),
    #     spec=kclient.V1PodSpec(restart_policy="Never", containers=[container]),
    # )

    # v1.create_namespaced_job(namespace=queue, body=body)


async def get_next_queue_item(queue: str):
    dsn = "postgresql://curibio_jobs_ro:HjnlH9RaeTt7uRuF7Uwco6BX4l0jgp39@localhost:5432/curibio"
    async with asyncpg.create_pool(dsn=dsn) as pool:
        async with pool.acquire() as con:
            records = await con.fetchrow(
                "SELECT meta->'version' AS version FROM jobs_queue WHERE queue=$1 ORDER BY priority DESC, created_at ASC",
                queue,
            )

            unique_versions = dict()
            for item in records:
                if item["version"] not in unique_versions:
                    unique_versions.append(item["version"])

            for version in unique_versions:
                await create_job(version, queue)


if __name__ == "__main__":
    # import os

    # DB_PASS = os.getenv("POSTGRES_PASSWORD")
    # DB_USER = os.getenv("POSTGRES_USER", default="curibio_jobs")
    # DB_HOST = os.getenv("POSTGRES_SERVER", default="psql-rds.default")
    # DB_NAME = os.getenv("POSTGRES_DB", default="curibio")
    # dsn = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
    # QUEUE = os.environ.get("QUEUE")
    QUEUE = "test-pulse3d"
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(get_next_queue_item(QUEUE))
    except Exception as e:
        print(f"EXCEPTION OCCURRED: {e}")
