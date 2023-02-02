import kopf
from kubernetes import config, client as kclient


# PRODUCT_QUEUES = ["pulse3d"]  # eventually pulse2d, nautilus, etc
# ECR_REPO = "077346344852.dkr.ecr.us-east-2.amazonaws.com/queue_processor"


# def create_queue_processors(queue: str = "test-pulse3d"):
def create_queue_processors(body, spec):
    print(body, spec)
    # # Configureate Pod template container
    # config.load_kube_config()
    # # config.load_incluster_config()
    # v1 = kclient.CoreV1Api()

    # QUEUE = kclient.V1EnvVar(name="QUEUE", value=queue)
    # POSTRES_PASSWORD = kclient.V1EnvVar(name="POSTGRES_PASSWORD", value="WrzVFnNDY9fkfNHt7JU5Wy9N")

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


@kopf.on.login(retries=1)
def login_fn(**kwargs):

    return config.load_incluster_config()


@kopf.on.create("test.net", "v1", "jobrunners")
async def create_fn(body, spec, **kwargs):
    await create_queue_processors(body, spec)


@kopf.on.delete("test.net", "v1", "jobrunners")
def delete(body, **kwargs):
    msg = f"Database {body['metadata']['name']} and its Pod / Service children deleted"
    return {"message": msg}
