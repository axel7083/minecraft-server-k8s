import json
import socket
import uuid
import time
from logging import Logger
from multiprocessing import Queue
from threading import Thread
from typing import Callable

import byte_utils


class SocketServer:
    def __init__(
            self,
            ip: str,
            port: int,
            version_text: str,
            kick_message: str,
            samples: [str],
            logger: Logger,
            show_hostname: bool,
            player_max: int,
            player_online: int,
            protocol: int,
            server_icon: str = None
    ):
        self.sock = None
        self.ip = ip
        self.port = port
        self.version_text = version_text
        self.kick_message = kick_message
        self.samples = samples
        self.server_icon = server_icon
        self.logger = logger
        self.show_hostname = show_hostname
        self.player_max = player_max
        self.player_online = player_online
        self.protocol = protocol
        self.running = False

        self.start_date = -1

    def get_motd_message(self) -> str:
        if self.start_date == -1:
            return "The server is currently offline\nIt will automatically start if a player try to connect."
        else:
            return "The server is start booting {seconds} seconds ago. It should be ready soon.".format(seconds=int(time.time()-self.start_date))

    def on_new_client(self, client_socket, addr, queue: Queue):
        data = client_socket.recv(1024)
        client_ip = addr[0]

        fqdn = socket.getfqdn(client_ip)
        if self.show_hostname and client_ip != fqdn:
            client_ip = fqdn + "/" + client_ip

        try:
            (length, i) = byte_utils.read_varint(data, 0)
            (packetID, i) = byte_utils.read_varint(data, i)

            if packetID == 0:
                (version, i) = byte_utils.read_varint(data, i)
                (ip, i) = byte_utils.read_utf(data, i)

                ip = ip.replace('\x00', '').replace("\r", "\\r").replace("\t", "\\t").replace("\n", "\\n")
                is_using_fml = False

                if ip.endswith("FML"):
                    is_using_fml = True
                    ip = ip[:-3]

                (port, i) = byte_utils.read_ushort(data, i)
                (state, i) = byte_utils.read_varint(data, i)

                if state == 1:
                    self.logger.info(("[%s:%s] Received client " + ("(using ForgeModLoader) " if is_using_fml else "") +
                                      "ping packet (%s:%s).") % (client_ip, addr[1], ip, port))
                    motd = {}
                    motd["version"] = {}
                    motd["version"]["name"] = self.version_text
                    motd["version"]["protocol"] = self.protocol
                    motd["players"] = {}
                    motd["players"]["max"] = self.player_max
                    motd["players"]["online"] = self.player_online
                    motd["players"]["sample"] = []

                    for sample in self.samples:
                        motd["players"]["sample"].append({"name": sample, "id": str(uuid.uuid4())})

                    motd["description"] = {"text": self.get_motd_message()}

                    if self.server_icon and len(self.server_icon) > 0:
                        motd["favicon"] = self.server_icon

                    self.write_response(client_socket, json.dumps(motd))
                elif state == 2:
                    name = ""
                    if len(data) != i:
                        (some_int, i) = byte_utils.read_varint(data, i)
                        (some_int, i) = byte_utils.read_varint(data, i)
                        (name, i) = byte_utils.read_utf(data, i)
                    self.logger.info(
                        ("[%s:%s] " + (name + " t" if len(name) > 0 else "T") + "ries to connect to the server " +
                         ("(using ForgeModLoader) " if is_using_fml else "") + "(%s:%s).")
                        % (client_ip, addr[1], ip, port))
                    self.write_response(client_socket, json.dumps({"text": self.kick_message}))
                    # Someone tried to connect
                    queue.put({"user": name})
                    if self.start_date == -1:
                        self.start_date = time.time()
                else:
                    self.logger.info(
                        "[%s:%d] Tried to request a login/ping with an unknown state: %d" % (client_ip, addr[1], state))
            elif packetID == 1:
                (long, i) = byte_utils.read_long(data, i)
                response = bytearray()
                byte_utils.write_varint(response, 9)
                byte_utils.write_varint(response, 1)
                bytearray.append(long)
                client_socket.sendall(bytearray)
                self.logger.info("[%s:%d] Responded with pong packet." % (client_ip, addr[1]))
            else:
                self.logger.warning("[%s:%d] Sent an unexpected packet: %d" % (client_ip, addr[1], packetID))
        except (TypeError, IndexError):
            self.logger.warning("[%s:%s] Received invalid data (%s)" % (client_ip, addr[1], data))
            return

    def write_response(self, client_socket, response):
        self.logger.info("write_response")
        response_array = bytearray()
        byte_utils.write_varint(response_array, 0)
        byte_utils.write_utf(response_array, response)
        length = bytearray()
        byte_utils.write_varint(length, len(response_array))
        client_socket.sendall(length)
        client_socket.sendall(response_array)

    def start(self, queue: Queue):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip, self.port))
        self.sock.settimeout(5000)
        self.sock.listen(30)
        self.running = True
        self.logger.info("Server started on %s:%s! Waiting for incoming connections..." % (self.ip, self.port))
        while self.running:
            (client, address) = self.sock.accept()
            Thread(target=self.on_new_client, args=(client, address, queue,)).start()

    def close(self):
        self.logger.info("Closing the socket")
        self.running = False
        self.sock.close()
