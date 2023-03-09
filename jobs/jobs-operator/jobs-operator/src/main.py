import kopf
from kubernetes import client as kclient
import os
import logging
import sys

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@kopf.on.create("curibio.dev", "v1", "jobrunners")
def create_fn(body, spec, **kwargs):
    namespace = body["metadata"]["namespace"]
    job_queue = spec["job_queue"]
    qp_name = f"{job_queue}-queue-processor"
    logger.info(f"Starting {qp_name} in namespace {namespace}")

    QUEUE_PROCESSOR_IMAGE = os.getenv("QUEUE_PROCESSOR_IMAGE")
    QUEUE_VAR = kclient.V1EnvVar(name="QUEUE", value=job_queue)
    ECR_REPO = kclient.V1EnvVar(name="ECR_REPO", value=spec["ecr_repo"])
    SECONDS_TO_POLL_DB = kclient.V1EnvVar(name="SECONDS_TO_POLL_DB", value=f"{spec['seconds_to_poll_db']}")
    MAX_JOBS_PER_WORKER = kclient.V1EnvVar(name="MAX_JOBS_PER_WORKER", value=f"{spec['max_jobs_per_worker']}")
    POSTGRES_USER = kclient.V1EnvVar(name="POSTGRES_USER", value=f"{job_queue}_queue_processor_ro")

    POSTGRES_PASSWORD = kclient.V1EnvVar(
        name="POSTGRES_PASSWORD",
        value_from=kclient.V1EnvVarSource(
            secret_key_ref=kclient.V1SecretKeySelector(
                name=f"{job_queue}-queue-processor-creds", key=f"{job_queue}_queue_processor_ro"
            )
        ),
    )
    # Create container
    container = kclient.V1Container(
        name=qp_name,
        image=QUEUE_PROCESSOR_IMAGE,
        env=[POSTGRES_PASSWORD, QUEUE_VAR, ECR_REPO, SECONDS_TO_POLL_DB, MAX_JOBS_PER_WORKER, POSTGRES_USER],
        image_pull_policy="Always",
    )

    # Deployment template
    deployment = {
        "apiVersion": "apps/v1",
        "metadata": {"name": f"{qp_name}", "labels": {"app": f"{job_queue}_qp"}},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": f"{job_queue}_qp"}},
            "template": {
                "metadata": {"labels": {"app": f"{job_queue}_qp"}},
                "spec": {"containers": [container]},
            },
        },
    }

    kopf.adopt(deployment, owner=body)
    # Object used to communicate with the API Server
    api = kclient.AppsV1Api()
    # Create deployment
    obj = api.create_namespaced_deployment(namespace, deployment)
    msg = f"Deployment {obj.metadata.name} created"
    return {"message": msg}


@kopf.on.delete("curibio.dev", "v1", "jobrunners")
def delete(body, **kwargs):
    msg = f"{body['metadata']['name']} and its Pod / Service children deleted"
    return {"message": msg}
