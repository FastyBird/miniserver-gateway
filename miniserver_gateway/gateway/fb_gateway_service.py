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
import logging
import time
from os import path
from threading import Thread
from yaml import safe_load
# App libs
from miniserver_gateway.connectors.connectors import Connectors
from miniserver_gateway.constants import LOG_LEVEL
from miniserver_gateway.exchanges.exchanges import Exchanges
from miniserver_gateway.db.models import db
from miniserver_gateway.db.cache import device_property_cache, channel_property_cache
from miniserver_gateway.storages.storages import Storages
from miniserver_gateway.triggers.triggers import Trigger

logging.basicConfig(level=LOG_LEVEL)
log = logging.getLogger("service")


#
# FastyBird gateway
#
# @package        FastyBird:MiniServer!
# @subpackage     Gateway
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class FBGatewayService:
    __configuration: dict
    __configuration_dir: str
    __stopped: bool = False

    __connectors: Connectors
    __storages: Storages
    __exchanges: Exchanges
    __triggers: Trigger

    __SHUTDOWN_WAITING_DELAY: int = 3.0

    # -----------------------------------------------------------------------------

    def __init__(
            self,
            config_file: str = None
    ) -> None:
        if config_file is None:
            config_file =\
                path.dirname(path.dirname(path.abspath(__file__))) +\
                "/config/fb_gateway.yaml".replace("/", path.sep)

        with open(config_file) as general_config:
            self.__configuration = safe_load(general_config)

        self.__configuration_dir = path.dirname(path.abspath(config_file)) + path.sep

        # Configure database
        db.bind(
            provider="mysql",
            host=self.__configuration.get("database").get("host", "127.0.0.1"),
            user=self.__configuration.get("database").get("user", "root"),
            passwd=self.__configuration.get("database").get("passwd", ""),
            db=self.__configuration.get("database").get("db", "miniserver_app")
        )
        db.generate_mapping(create_tables=False)
        # orm.set_sql_debug()

        # Initialize data exchanges
        exchanges_configuration: list = list(self.__configuration.get("exchanges", {}))
        self.__exchanges = Exchanges(exchanges_configuration)

        # Initialize data storages
        storages_configuration: list = list(self.__configuration.get("storages", {}))
        self.__storages = Storages(storages_configuration)

        # Initialize connectors
        connectors_configuration: list = list(self.__configuration.get("connectors", {}))
        self.__connectors = Connectors(connectors_configuration)

        self.__triggers = Trigger()

        # Initialize repository cache
        device_property_cache.initialize()
        channel_property_cache.initialize()

        # Start all connectors
        self.__connectors.open()

        try:
            while not self.__stopped:
                # Just to keep GW running
                pass

        except KeyboardInterrupt:
            self.__stop_gateway()

        except Exception as e:
            log.exception(e)

            self.__stop_gateway()

            log.info("The gateway has been stopped.")

    # -----------------------------------------------------------------------------

    def __stop_gateway(
            self
    ) -> None:
        self.__stopped = True

        log.info("Stopping...")

        # Send terminate command to...

        # ...all connectors
        self.__connectors.close()

        # ...and wait until thread is fully terminated
        self.__wait_for_thread_to_close(self.__connectors)

        log.info("All connectors were closed")

        # ...and rest of services
        self.__exchanges.close()

        # ...and wait until thread is fully terminated
        self.__wait_for_thread_to_close(self.__exchanges)

        log.info("Data exchanges service was closed")

        # ...all storages
        self.__storages.close()

        # ...and wait until thread is fully terminated
        self.__wait_for_thread_to_close(self.__storages)

        log.info("Data storage service was closed")

        log.info("============================")
        log.info("The gateway has been stopped")

    # -----------------------------------------------------------------------------

    def __wait_for_thread_to_close(
            self,
            thread_service: Thread
    ) -> None:
        now: float = time.time()

        waiting_for_closing: bool = True

        # Wait until thread is fully terminated
        while waiting_for_closing and time.time() - now < self.__SHUTDOWN_WAITING_DELAY:
            if not thread_service.is_alive():
                waiting_for_closing = False
