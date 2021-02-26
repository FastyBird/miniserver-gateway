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
from time import sleep
from redis import Redis
from redis.client import PubSub
from threading import Thread

# App libs
from miniserver_gateway.constants import APP_ORIGIN
from miniserver_gateway.exchanges.exchanges import log, Exchanges, ExchangeInterface


#
# Redis exchanges settings
#
# @package        FastyBird:MiniServer!
# @subpackage     Exchange
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class RedisExchangeSettings:
    __host: str = "127.0.0.1"
    __port: int = 6379
    __username: str or None = None
    __password: str or None = None

    # -----------------------------------------------------------------------------

    def __init__(self, config: dict) -> None:
        self.__host = config.get("host", "127.0.0.1")
        self.__port = int(config.get("port", 6379))
        self.__username = config.get("username", None)
        self.__password = config.get("password", None)

    # -----------------------------------------------------------------------------

    @property
    def host(self) -> str:
        return self.__host

    # -----------------------------------------------------------------------------

    @property
    def port(self) -> int:
        return self.__port

    # -----------------------------------------------------------------------------

    @property
    def username(self) -> str or None:
        return self.__username

    # -----------------------------------------------------------------------------

    @property
    def password(self) -> str or None:
        return self.__password


#
# Redis exchanges interface
#
# @package        FastyBird:MiniServer!
# @subpackage     Exchange
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class RedisExchange(ExchangeInterface, Thread):
    __stopped: bool = False

    __redis_client: Redis
    __redis_pub_sub: PubSub

    __container: Exchanges

    __settings: RedisExchangeSettings

    __CHANNEL_NAME: str = "fb_exchange"

    # -----------------------------------------------------------------------------

    def __init__(self, config: dict, exchange: Exchanges) -> None:
        Thread.__init__(self)
        ExchangeInterface.__init__(self, config)

        self.__container = exchange

        self.__settings = RedisExchangeSettings(config)

        self.__redis_client = Redis(
            host=self.__settings.host, port=self.__settings.port
        )
        self.__redis_pub_sub = self.__redis_client.pubsub()

        self.__redis_pub_sub.subscribe(self.__CHANNEL_NAME)

        # Threading config...
        self.setName("Redis exchanges thread")
        # ...and starting
        self.start()

    # -----------------------------------------------------------------------------

    def run(self) -> None:
        self.__stopped = False

        while not self.__stopped:
            result = self.__redis_pub_sub.get_message()

            if result is not None and result.get("type") == "message":
                received_data = result.get("data", bytes("{}", "utf-8"))

                if isinstance(received_data, bytes):
                    self.__container.process_received_message(
                        received_data.decode("utf-8")
                    )

            sleep(0.001)

    # -----------------------------------------------------------------------------

    def close(self) -> None:
        self.__stopped = True

        # Disconnect from server
        self.__redis_pub_sub.unsubscribe(self.__CHANNEL_NAME)

    # -----------------------------------------------------------------------------

    def publish(self, routing_key: str, data: dict) -> None:
        message: dict = {
            "routing_key": routing_key,
            "origin": APP_ORIGIN,
            "data": data,
        }

        result: int = self.__redis_client.publish(
            self.__CHANNEL_NAME, json.dumps(message)
        )

        log.debug(
            "Successfully published message to: {} consumers via Redis with key: {}".format(
                result, routing_key
            )
        )
