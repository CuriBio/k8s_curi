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


@kopf.on.create("test.net", "v1", "jobrunners")  # TODO look at how to change the on create to prod.net
def create_fn(body, spec, **kwargs):
    # Get info from grafana object
    namespace = body["metadata"]["namespace"]
    job_queue = spec["job_queue"]
    qp_name = f"{job_queue}-queue-processor"
    logger.info(f"Starting {qp_name} in namespace {namespace}")

    POSTGRES_PASSWORD = kclient.V1EnvVar(name="POSTGRES_PASSWORD", value=os.getenv("POSTGRES_PASSWORD"))
    QUEUE_VAR = kclient.V1EnvVar(name="QUEUE", value=job_queue)
    ECR_REPO = kclient.V1EnvVar(name="ECR_REPO", value=spec["ecr_repo"])
    SECONDS_TO_POLL_DB = kclient.V1EnvVar(name="SECONDS_TO_POLL_DB", value=f"{spec['seconds_to_poll_db']}")
    MAX_JOBS_PER_WORKER = kclient.V1EnvVar(name="MAX_JOBS_PER_WORKER", value=f"{spec['max_jobs_per_worker']}")

    # Create container
    container = kclient.V1Container(
        name=qp_name,
        image="077346344852.dkr.ecr.us-east-2.amazonaws.com/queue-processor:0.0.1",
        env=[POSTGRES_PASSWORD, QUEUE_VAR, ECR_REPO, SECONDS_TO_POLL_DB, MAX_JOBS_PER_WORKER],
        image_pull_policy="Always",
    )

    # Deployment template
    deployment = {
        "apiVersion": "apps/v1",
        "metadata": {"name": f"{qp_name}", "labels": {"app": job_queue}},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": job_queue}},
            "template": {
                "metadata": {"labels": {"app": job_queue}},
                "spec": {"containers": [container]},
            },
        },
    }

    # Make the Pod and Service the children of the grafana object
    kopf.adopt(deployment, owner=body)
    # Object used to communicate with the API Server
    api = kclient.AppsV1Api()

    # Create deployment
    obj = api.create_namespaced_deployment(namespace, deployment)
    msg = f"Deployment {obj.metadata.name} created"
    return {"message": msg}


@kopf.on.delete("test.net", "v1", "jobrunners")
def delete(body, **kwargs):
    msg = f"{body['metadata']['name']} and its Pod / Service children deleted"
    return {"message": msg}
