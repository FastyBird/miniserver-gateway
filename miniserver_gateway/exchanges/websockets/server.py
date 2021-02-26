#!/usr/bin/python3

#     Copyright 2021. FastyBird s.r.o.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

# App dependencies
import socket
import ssl
from select import select
from threading import Thread
from typing import Dict, List

# App libs
from miniserver_gateway.exchanges.websockets.client import WampClient
from miniserver_gateway.exchanges.websockets.types import OPCodes


class WebsocketsServer(Thread):
    __stopped: bool = False

    __request_queue_size: int = 5
    __select_interval: float = 0.1

    __using_ssl: bool = False

    __server_socket: socket.socket

    __listeners: List[int or socket.socket] = []
    __connections: Dict[int, WampClient] = {}

    __secured_context: ssl.SSLContext or None

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        host: str = "",
        port: int = 9000,
        cert_file: str or None = None,
        key_file: str or None = None,
        ssl_version: int = ssl.PROTOCOL_TLSv1,
        select_interval: float = 0.1,
    ) -> None:
        Thread.__init__(self)

        if host == "":
            host = None

        fam = socket.AF_INET6 if host is None else 0

        host_info = socket.getaddrinfo(
            host, port, fam, socket.SOCK_STREAM, socket.IPPROTO_TCP, socket.AI_PASSIVE
        )

        self.__server_socket = socket.socket(
            host_info[0][0], host_info[0][1], host_info[0][2]
        )
        self.__server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__server_socket.bind(host_info[0][4])
        self.__server_socket.listen(self.__request_queue_size)

        self.__select_interval = select_interval

        self.__listeners = [self.__server_socket]

        self.__using_ssl = bool(cert_file and key_file)

        if self.__using_ssl:
            self.__secured_context = ssl.SSLContext(ssl_version)
            self.__secured_context.load_cert_chain(cert_file, key_file)

        # Threading config...
        self.setDaemon(True)
        self.setName("WebSockets server exchanges")
        # ...and starting
        self.start()

    # -----------------------------------------------------------------------------

    def run(self) -> None:
        self.__stopped = False

        while not self.__stopped:
            self.__handle_request()

    # -----------------------------------------------------------------------------

    def close(self) -> None:
        self.__stopped = True

        self.__server_socket.close()

        for desc, conn in self.__connections.items():
            conn.send_close()

            self.__handle_close(conn)

    # -----------------------------------------------------------------------------

    def __handle_request(self) -> None:
        writers = []

        for fileno in self.__listeners:
            if fileno == self.__server_socket:
                continue

            client = self.__connections[fileno]

            if client.get_send_queue():
                writers.append(fileno)

        if self.__select_interval:
            r_list, w_list, x_list = select(
                self.__listeners, writers, self.__listeners, self.__select_interval
            )

        else:
            r_list, w_list, x_list = select(self.__listeners, writers, self.__listeners)

        for ready in w_list:
            client = self.__connections[ready]

            try:
                while client.get_send_queue():
                    opcode, payload = client.get_send_queue().popleft()
                    remaining = client.send_buffer(payload)

                    if remaining is not None:
                        client.get_send_queue().appendleft((opcode, remaining))
                        break

                    if opcode == OPCodes(OPCodes.CLOSE).value:
                        raise Exception("Received client close")

            except Exception:
                self.__handle_close(client)

                del self.__connections[ready]

                self.__listeners.remove(ready)

        for ready in r_list:
            if ready == self.__server_socket:
                sock = None

                try:
                    sock, address = self.__server_socket.accept()

                    client_socket = self.__decorate_socket(sock)
                    client_socket.setblocking(False)

                    fileno = client_socket.fileno()

                    self.__connections[fileno] = WampClient(client_socket, address)

                    self.__listeners.append(fileno)

                except Exception:
                    if sock is not None:
                        sock.close()

            else:
                if ready not in self.__connections:
                    continue

                client = self.__connections[ready]

                try:
                    client.receive_data()

                except Exception:
                    self.__handle_close(client)

                    del self.__connections[ready]

                    self.__listeners.remove(ready)

        for failed in x_list:
            if failed == self.__server_socket:
                self.close()

                raise Exception("Server socket failed")

            if failed not in self.__connections:
                continue

            client = self.__connections[failed]

            self.__handle_close(client)

            del self.__connections[failed]

            self.__listeners.remove(failed)

    # -----------------------------------------------------------------------------

    def __decorate_socket(self, sock: socket.socket) -> socket.socket:
        if self.__using_ssl:
            return self.__secured_context.wrap_socket(sock, server_side=True)

        return sock

    # -----------------------------------------------------------------------------

    @staticmethod
    def __handle_close(client: WampClient):
        client.sock.close()

        # only call handle_close when we have a successful websocket connection
        if client.handshake_finished():
            try:
                client.handle_close()

            except Exception:
                pass
