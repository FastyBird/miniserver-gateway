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
import json
import time
from typing import Dict

# App libs
from miniserver_gateway.constants import APP_ORIGIN, WS_SERVER_TOPIC
from miniserver_gateway.events.dispatcher import app_dispatcher
from miniserver_gateway.exchanges.exchanges import log, Exchanges, ExchangeInterface
from miniserver_gateway.exchanges.websockets.events import (
    SubscribeEvent,
    UnsubscribeEvent,
    ReceiveProcedureRequestEvent,
)
from miniserver_gateway.exchanges.websockets.client import WampClientInterface
from miniserver_gateway.exchanges.websockets.types import WampCodes
from miniserver_gateway.exchanges.websockets.server import WebsocketsServer


#
# WS WAMP client exchanges interface
#
# @package        FastyBird:MiniServer!
# @subpackage     Exchange
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class WampExchange(ExchangeInterface):
    __subscribers: Dict[str, WampClientInterface] = {}

    __container: Exchanges

    __ws_server: WebsocketsServer

    __SHUTDOWN_WAITING_DELAY: int = 3.0

    # -----------------------------------------------------------------------------

    def __init__(self, config: dict, exchange: Exchanges) -> None:
        super().__init__(config)

        self.__container = exchange

        app_dispatcher.add_listener(SubscribeEvent.EVENT_NAME, self.__subscribe)
        app_dispatcher.add_listener(UnsubscribeEvent.EVENT_NAME, self.__unsubscribe)
        app_dispatcher.add_listener(
            ReceiveProcedureRequestEvent.EVENT_NAME, self.__receive
        )

        # WS server for UI clients
        self.__ws_server = WebsocketsServer()

    # -----------------------------------------------------------------------------

    def close(self) -> None:
        # Terminate web sockets server
        self.__ws_server.close()

        now: float = time.time()

        waiting_for_closing: bool = True

        # ...and wait until server is fully terminated
        while waiting_for_closing and time.time() - now < self.__SHUTDOWN_WAITING_DELAY:
            if not self.__ws_server.is_alive():
                waiting_for_closing = False

        log.info("Web sockets server service was closed")

    # -----------------------------------------------------------------------------

    def publish(self, routing_key: str, data: dict) -> None:
        message: dict = {
            "routing_key": routing_key,
            "origin": APP_ORIGIN,
            "data": data,
        }

        for client in self.__subscribers.values():
            client.send_message(
                json.dumps(
                    [
                        WampCodes(WampCodes.MSG_EVENT).value,
                        WS_SERVER_TOPIC,
                        json.dumps(message),
                    ]
                )
            )

        log.debug(
            "Successfully published message to: {} consumers via WS with key: {}".format(
                len(self.__subscribers), routing_key
            )
        )

    # -----------------------------------------------------------------------------

    def __receive(self, event: ReceiveProcedureRequestEvent) -> None:
        try:
            if self.__container.process_received_message(event.data):
                event.client.send_message(
                    json.dumps(
                        [
                            WampCodes(WampCodes.MSG_CALL_RESULT).value,
                            event.rpc_id,
                            {
                                "response": "accepted",
                            },
                        ]
                    )
                )

            else:
                event.client.send_message(
                    json.dumps(
                        [
                            WampCodes(WampCodes.MSG_CALL_ERROR).value,
                            event.rpc_id,
                            {
                                "response": "Provided message could not be handled",
                            },
                        ]
                    )
                )

        except Exception as e:
            log.exception(e)

            event.client.send_message(
                json.dumps(
                    [
                        WampCodes(WampCodes.MSG_CALL_ERROR).value,
                        event.rpc_id,
                        {
                            "response": "Provided message could not be handled",
                        },
                    ]
                )
            )

    # -----------------------------------------------------------------------------

    def __subscribe(self, event: SubscribeEvent) -> None:
        if event.client.get_id() not in self.__subscribers.keys():
            self.__subscribers[event.client.get_id()] = event.client

            log.info(
                "New client: {} has subscribed to exchanges topic".format(
                    event.client.get_id()
                )
            )

    # -----------------------------------------------------------------------------

    def __unsubscribe(self, event: UnsubscribeEvent) -> None:
        if event.client.get_id() in self.__subscribers.keys():
            del self.__subscribers[event.client.get_id()]

            log.info(
                "Client: {} has unsubscribed from exchanges topic".format(
                    event.client.get_id()
                )
            )
