import logging
from kubernetes.client import CoreV1Api, AppsV1Api
from mcstatus import JavaServer
from enum import Enum
import time, threading
from socket_server import SocketServer
from threading import main_thread
from multiprocessing import Process, Queue


class ServerStatus(Enum):
    UNKNOWN = 1
    RUNNING = 2
    OFFLINE = 3
    BOOTING = 4


def setup_logger(name: str):
    logger = logging.getLogger(name)

    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('[%(threadName)s] %(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    return logger


class ServerManager:

    def __init__(self, core_v1: CoreV1Api, apps_v1: AppsV1Api, permanent_host: str, service: str, deployment: str, namespace: str, waiting_time: int):
        self.logger = setup_logger("ServerManager")
        self.logger.info("Init ServerManager")
        self.fake_server = SocketServer(
            ip="0.0.0.0",
            port=25565,
            version_text="Offline",
            kick_message="The server will start booting soon.",
            samples=["Hello", "", "ouioui"],
            server_icon="server_icon.png",
            logger=self.logger.getChild("SocketServer"),
            show_hostname=True,
            player_max=0,
            player_online=0,
            protocol=2
        )
        self.permanent_host = permanent_host
        self.service: str = service
        self.deployment: str = deployment
        self.namespace: str = namespace
        self.waiting_time: int = waiting_time

        self.server = JavaServer.lookup(self.permanent_host)
        self.zero_count: int = 0
        self.status = ServerStatus.UNKNOWN
        self.start_date = -1

        self.coreV1 = core_v1
        self.appsV1 = apps_v1

        self.socket_process = None
        self.queue = None

    def ping(self) -> bool:
        try:
            status = self.server.status()

            if status.players.online == 0:
                self.zero_count = self.zero_count + 1
            else:
                self.zero_count = 0
            return True
        except Exception as e:
            return False

    def job(self):
        self.logger.info("running job with status {status}".format(status=self.status))

        delay = self.waiting_time

        # handle Unknown in a specific way
        if self.status is ServerStatus.UNKNOWN:
            self.handle_unknown()

        if self.status is ServerStatus.RUNNING:
            self.handle_running()
        elif self.status is ServerStatus.BOOTING:
            self.handle_booting()
            delay = 30
        elif self.status is ServerStatus.OFFLINE:
            self.handle_offline()

        time.sleep(delay)
        self.job()

    def handle_unknown(self):
        # Get the replicas count
        count = self.appsV1.read_namespaced_deployment_scale(self.deployment, self.namespace).status.replicas
        if count == 0:
            self.status = ServerStatus.OFFLINE
        elif self.ping():
            self.status = ServerStatus.RUNNING
            self.redirect_service('minecraft-server')
        else:
            self.status = ServerStatus.BOOTING

    def redirect_service(self, name):
        self.coreV1.patch_namespaced_service(
            name=self.service,
            namespace=self.namespace,
            body={'spec': {'selector': {'app.kubernetes.io/name': name}}}
        )

    def handle_running(self):
        if self.ping():
            self.status = ServerStatus.RUNNING
            if self.zero_count > 2:
                self.stop_java_server()
                self.setup_fake_server()
        else:
            self.status = ServerStatus.OFFLINE
            if not self.fake_server.running:
                self.setup_fake_server()

    def handle_booting(self):
        if self.ping():
            self.status = ServerStatus.RUNNING
            self.stop_fake_server()
        elif time.time() - self.start_date > 10 * 60:
            self.logger.warning("The server has not started yet, it was launched 10 minutes ago.")

    def handle_offline(self):
        if self.socket_process is None or not self.socket_process.is_alive():
            self.setup_fake_server()

    def setup_fake_server(self):
        self.logger.info("Setup the fake server")

        # patch_namespaced_service
        self.redirect_service('minecraft-fake-server')
        self.queue = Queue()
        self.socket_process = Process(name="Socket", daemon=True, target=self.fake_server.start, args=(self.queue,))
        self.socket_process.start()
        self.logger.info("Main-Thread blocked.")
        request = self.queue.get(block=True)
        self.logger.info("Main-Thread unblocked.")

        self.logger.info(f'User {request["user"]} is trying to join.')
        self.on_connection()

    def stop_fake_server(self):
        self.logger.info("Stopping the fake server")
        if self.socket_process.is_alive():
            self.redirect_service('minecraft-server')
            self.fake_server.close()
            self.logger.info("fake server terminated.")

    def stop_java_server(self):
        self.logger.info("Stopping the java server")

        self.appsV1.patch_namespaced_deployment_scale(
            name=self.deployment,
            namespace=self.namespace,
            body={'spec': {'replicas': 0}}
        )
        self.status = ServerStatus.OFFLINE

    def start_java_server(self):
        self.logger.info("Starting the java server")
        self.zero_count = 0
        self.start_date = time.time()
        self.appsV1.patch_namespaced_deployment_scale(
            name=self.deployment,
            namespace=self.namespace,
            body={'spec': {'replicas': 1}}
        )
        self.status = ServerStatus.BOOTING

    # This function will be called from the SockerThread
    def on_connection(self):
        if self.status is ServerStatus.BOOTING:
            return

        self.logger.info("Connection received, starting MC Java Server")
        self.start_java_server()
        self.job()
