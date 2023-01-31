# import kopf
from kubernetes import config, client as kclient



PRODUCT_QUEUES = ["pulse3d"]  # eventually pulse2d, nautilus, etc
ECR_REPO = "077346344852.dkr.ecr.us-east-2.amazonaws.com/queue_processor"


def create_queue_processors(queue: str = "test-pulse3d"):
    # Configureate Pod template container
    config.load_kube_config()  # TODO remove
    v1 = kclient.CoreV1Api()

    queue_env = kclient.V1EnvVar(name="QUEUE", value=queue)

    container = kclient.V1Container(
        name="queue-processor", image=ECR_REPO, command=["python", "main.py"], env=[queue_env]
    )

    # Create and configure a spec section
    body = kclient.V1PodTemplateSpec(
        metadata=kclient.V1ObjectMeta(name=f"{queue}-queue-processor", labels={"app": "queue_processor"}),
        spec=kclient.V1PodSpec(restart_policy="Never", containers=[container]),
    )

    v1.create_namespaced_pod(namespace=queue, body=body)


# @kopf.on.create("test", "v1", "job_runner")
# async def create_fn(body, spec, **kwargs):
#     # Get info from Database object
#     name = body["metadata"]["name"]
#     namespace = body["metadata"]["namespace"]
#     # type = spec['type']

#     # Make sure type is provided
#     # if not type:
#     #     raise kopf.HandlerFatalError(f"Type must be set. Got {type}.")

#     # Pod template
#     pod = {"apiVersion": "v1", "metadata": {"name": name, "labels": {"app": "db"}}}

#     processor = create_queue_processor()

#     kopf.adopt(processor, owner=body)

#     # # Service template
#     # svc = {'apiVersion': 'v1', 'metadata': {'name' : name}, 'spec': { 'selector': {'app': 'db'}, 'type': 'NodePort'}}

#     # Object used to communicate with the API Server
#     # api = kclient.CoreV1Api()
#     api = kclient.BatchV1Api()

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
