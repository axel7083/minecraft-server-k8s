from ServerManager import ServerManager
from kubernetes import client, config
import os


def get_env(name: str) -> str:
    value = os.getenv(name)
    # Ensure MC_ADDRESS exist
    if value is None or value == "":
        raise Exception("{env} env cannot be empty.".format(env=name))
    return value


def main():
    config.load_incluster_config()

    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()

    permanent_host = get_env("PERMANENT_HOST")
    service: str = get_env("K8S_MC_SERVICE")
    deployment: str = get_env("K8S_MC_DEPLOYMENT")
    namespace: str = get_env("K8S_MC_NAMESPACE")
    waiting_time: int = int(get_env("WAITING_TIME"))

    server_manager = ServerManager(
        core_v1=core_v1,
        apps_v1=apps_v1,
        permanent_host=permanent_host,
        service=service,
        deployment=deployment,
        namespace=namespace,
        waiting_time=waiting_time
    )
    server_manager.job()




if __name__ == '__main__':
    main()
