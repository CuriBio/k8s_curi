import kopf
from kubernetes import config, client as kclient
import os


# def create_queue_processors(queue: str = "test-pulse3d"):
# async def create_queue_processors(body, spec):
#     print("2: ", body, spec)
#     # Configureate Pod template container
#     v1 = kclient.CoreV1Api()
#     QUEUE = kclient.V1EnvVar(name="QUEUE")
#     POSTRES_PASSWORD = kclient.V1EnvVar(name="POSTGRES_PASSWORD", value=os.getenv("POSTGRES_PASSWORD"))

# container = kclient.V1Container(
#     name="queue-processor",
#     image=ECR_REPO,
#     command=["python", "main.py"],
#     env=[QUEUE, POSTRES_PASSWORD],
# )

# # Create and configure a spec section
# body = kclient.V1PodTemplateSpec(
#     metadata=kclient.V1ObjectMeta(name=f"{queue}-queue-processor", labels={"app": "queue_processor"}),
#     spec=kclient.V1PodSpec(
#         restart_policy="Never", containers=[container], service_account_name="queue-processor"
#     ),
# )
# kopf.adopt(pod, owner=body)

# v1.create_namespaced_pod(namespace="pulse3d", body=body)  # TODO change back to queue


# @kopf.on.create("test.net", "v1", "jobrunners")
# async def create_fn(body, spec, **kwargs):
#     await create_queue_processors(body, spec)


# @kopf.on.delete("test.net", "v1", "jobrunners")
# def delete(body, **kwargs):
#     msg = f"Database {body['metadata']['name']} and its Pod / Service children deleted"
#     return {"message": msg}


# import kopf
# import kubernetes


@kopf.on.create("test.net", "v1", "jobrunners")
def create_fn(body, spec, **kwargs):

    # Get info from grafana object
    name = body["metadata"]["name"]
    namespace = body["metadata"]["namespace"]
    job_queue = spec["job_queue"]
    qp_name = f"{job_queue}-queue-processor"

    POSTGRES_PASSWORD = kclient.V1EnvVar(name="POSTGRES_PASSWORD", value=os.getenv("POSTGRES_PASSWORD"))
    QUEUE_VAR = kclient.V1EnvVar(name="QUEUE", value=job_queue)
    ECR_REPO = kclient.V1EnvVar(name="ECR_REPO", value=spec["ecr_repo"])

    # Create container
    container = kclient.V1Container(
        name=qp_name,
        image="077346344852.dkr.ecr.us-east-2.amazonaws.com/queue-processor:0.0.1",
        env=[POSTGRES_PASSWORD, QUEUE_VAR, ECR_REPO],
    )
    
    # Deployment template
    deployment = {
        "apiVersion": "v1",
        "kind": "Deployment",
        "metadata": {"name": f"{qp_name}", "labels": {"app": job_queue}},
        "spec": {"containers": [container]},
    }

    # Make the Pod and Service the children of the grafana object
    kopf.adopt(deployment, owner=body)
    # Object used to communicate with the API Server
    api = kclient.CoreV1Api()

    # Create deployment    
    obj = api.create_namespaced_deployment(namespace, deployment)
    print(f"Deployment {obj.metadata.name} created")

    msg = f"Pod and Service created for jobRunner object {name}"
    return {"message": msg}


@kopf.on.delete("test.net", "v1", "jobrunners")
def delete(body, **kwargs):
    msg = f"{body['metadata']['name']} and its Pod / Service children deleted"
    return {"message": msg}
