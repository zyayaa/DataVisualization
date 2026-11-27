import docker

CONTAINER_NAME = "sandbox"
client = docker.from_env()

def sandbox():
    return client.containers.get(CONTAINER_NAME)
