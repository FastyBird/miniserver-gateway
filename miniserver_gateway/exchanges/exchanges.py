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
import logging
import time
from abc import ABC, abstractmethod
from queue import Queue, Full as QueueFull
from threading import Thread
from typing import Dict, List, Set
# App libs
from miniserver_gateway.constants import APP_ORIGIN, LOG_LEVEL
from miniserver_gateway.db.cache import device_property_cache, channel_property_cache, \
    DevicePropertyItem, ChannelPropertyItem
from miniserver_gateway.db.events import DatabaseEntityChangedEvent
from miniserver_gateway.events.dispatcher import app_dispatcher
from miniserver_gateway.exchanges.events import ExchangePropertyExpectedValueEvent
from miniserver_gateway.exchanges.queue import PublishPropertyValueQueueItem, PublishEntityQueueItem
from miniserver_gateway.exchanges.utils import ExchangeRoutingUtils
from miniserver_gateway.exchanges.types import RoutingKeys
from miniserver_gateway.storages.events import StoragePropertyStoredEvent
from miniserver_gateway.utils.libraries import LibrariesUtils

logging.basicConfig(level=LOG_LEVEL)
log = logging.getLogger("exchanges")


#
# Storages container settings
#
# @package        FastyBird:MiniServer!
# @subpackage     Exchange
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class ExchangeSettings:
    __exchanges: List[Dict[str, str]] = {}

    # -----------------------------------------------------------------------------

    def __init__(
            self,
            config: List[Dict[str, str]]
    ) -> None:
        self.__exchanges = config

    # -----------------------------------------------------------------------------

    def all(
            self
    ) -> List[Dict[str, str]]:
        return self.__exchanges


#
# Storages container
#
# @package        FastyBird:MiniServer!
# @subpackage     Exchange
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class Exchanges(Thread):
    __stopped: bool = False

    __settings: ExchangeSettings

    __exchanges: Set["ExchangeInterface"] = set()

    __queue: Queue

    __SHUTDOWN_WAITING_DELAY: int = 3.0

    # -----------------------------------------------------------------------------

    def __init__(
            self,
            config: List[Dict[str, str]]
    ) -> None:
        super().__init__()

        self.__settings = ExchangeSettings(config)

        app_dispatcher.add_listener(StoragePropertyStoredEvent.EVENT_NAME, self.__publish_stored_value)
        app_dispatcher.add_listener(DatabaseEntityChangedEvent.EVENT_NAME, self.__publish_entity)

        # Queue for consuming incoming data from connectors
        self.__queue = Queue(maxsize=1000)

        # Process storages services
        self.__load()

        # Threading config...
        self.setDaemon(True)
        self.setName("Exchange thread")
        # ...and starting
        self.start()

    # -----------------------------------------------------------------------------

    def run(
            self
    ) -> None:
        self.__stopped = False

        while True:
            if not self.__queue.empty():
                record = self.__queue.get()

                if isinstance(record, PublishPropertyValueQueueItem):
                    self.__process_property_value_record(record)

                elif isinstance(record, PublishEntityQueueItem):
                    self.__process_entity_record(record)

            # All records have to be processed before thread is closed
            if self.__stopped and self.__queue.empty():
                break

            time.sleep(0.001)

    # -----------------------------------------------------------------------------

    def close(
            self
    ) -> None:
        """Stop exchanges main thread"""

        self.__stopped = True

        for exchange in self.__exchanges:
            try:
                # Send terminate cmd to all sub-exchanges
                exchange.close()

            except Exception as e:
                log.exception(e)

        now: float = time.time()

        waiting_for_closing: bool = True

        # Wait until all sub-exchanges are fully terminated
        while waiting_for_closing and time.time() - now < self.__SHUTDOWN_WAITING_DELAY:
            one_alive: bool = False

            for exchange in self.__exchanges:
                if isinstance(exchange, Thread) and exchange.is_alive() is True:
                    one_alive = True

            if not one_alive:
                waiting_for_closing = False

    # -----------------------------------------------------------------------------

    def process_received_message(
            self,
            received_data: str
    ) -> bool:
        """Process received message by sub-exchanges"""

        try:
            parsed_data: dict = json.loads(received_data)

            if (
                    parsed_data.get("routing_key", None) is not None
                    and isinstance(parsed_data.get("routing_key", None), str) is True
                    and parsed_data.get("origin", None) is not None
                    and isinstance(parsed_data.get("origin", None), str) is True
                    and parsed_data.get("data", None) is not None
                    and (
                        isinstance(parsed_data.get("data", None), str) is True
                        or isinstance(parsed_data.get("data", None), dict) is True
                    )
            ):
                return self.__process_message(
                    parsed_data.get("routing_key", None),
                    parsed_data.get("origin", None),
                    parsed_data.get("data", None)
                )

        except json.JSONDecodeError as e:
            log.exception(e)

        return False

    # -----------------------------------------------------------------------------

    def __publish_stored_value(
            self,
            event: StoragePropertyStoredEvent
    ) -> None:
        """Process storage service save event"""

        try:
            if isinstance(event.record, DevicePropertyItem) or isinstance(event.record, ChannelPropertyItem):
                self.__queue.put(PublishPropertyValueQueueItem(
                    event.record,
                    event.value,
                    event.expected_value,
                    event.is_pending,
                ))

            else:
                log.warning("Received unknown storage event")

        except QueueFull:
            log.error("Exchange processing queue is full. New messages could not be added")

    # -----------------------------------------------------------------------------

    def __publish_entity(
            self,
            event: DatabaseEntityChangedEvent
    ) -> None:
        """Process database entity changed event"""

        try:
            routing_key = ExchangeRoutingUtils.get_entity_routing_key(type(event.entity), event.action_type)

            if routing_key is not None:
                self.__queue.put(PublishEntityQueueItem(
                    routing_key,
                    event.entity.to_array()
                ))

        except QueueFull:
            log.error("Exchange processing queue is full. New messages could not be added")

    # -----------------------------------------------------------------------------

    @staticmethod
    def __process_message(
            routing_key: str,
            origin: str,
            data: dict or str or None
    ) -> bool:
        # Check if received message was not sent by gateway
        if origin != APP_ORIGIN:
            if (
                    routing_key == RoutingKeys(RoutingKeys.DEVICES_PROPERTIES_DATA_ROUTING_KEY).value
                    or routing_key == RoutingKeys(RoutingKeys.CHANNELS_PROPERTIES_DATA_ROUTING_KEY).value
            ):
                # TODO: Add json validation for data

                if data is not None:
                    if routing_key == RoutingKeys(RoutingKeys.DEVICES_PROPERTIES_DATA_ROUTING_KEY).value:
                        device_property = device_property_cache.get_property_by_key(data.get("property"))

                        if device_property is not None:
                            app_dispatcher.dispatch(
                                ExchangePropertyExpectedValueEvent.EVENT_NAME,
                                ExchangePropertyExpectedValueEvent(
                                    device_property,
                                    data.get("expected")
                                )
                            )

                            return True

                        else:
                            log.warning(
                                "Received message for unknown device property: {}"
                                .format(data.get("property"))
                            )

                    elif routing_key == RoutingKeys(RoutingKeys.CHANNELS_PROPERTIES_DATA_ROUTING_KEY).value:
                        channel_property = channel_property_cache.get_property_by_key(data.get("property"))

                        if channel_property is not None:
                            app_dispatcher.dispatch(
                                ExchangePropertyExpectedValueEvent.EVENT_NAME,
                                ExchangePropertyExpectedValueEvent(
                                    channel_property,
                                    data.get("expected")
                                )
                            )

                            return True

                        else:
                            log.warning(
                                "Received message for unknown channel property: {}"
                                .format(data.get("property"))
                            )

                else:
                    log.warning("Received data message without data")

        return False

    # -----------------------------------------------------------------------------

    def __process_property_value_record(
            self,
            record: PublishPropertyValueQueueItem
    ) -> None:
        """Consume queue record with device or channel property updates"""

        if isinstance(record.item, DevicePropertyItem):
            routing_key: str = RoutingKeys(RoutingKeys.DEVICES_PROPERTY_UPDATED_ENTITY_ROUTING_KEY).value

        elif isinstance(record.item, ChannelPropertyItem):
            routing_key: str = RoutingKeys(RoutingKeys.CHANNELS_PROPERTY_UPDATED_ENTITY_ROUTING_KEY).value

        else:
            # Unknown record item
            return

        content: dict = record.item.to_array()
        content["value"] = record.value
        content["expected"] = record.expected_value
        content["pending"] = record.is_pending

        for exchange in self.__exchanges:
            exchange.publish(routing_key, content)

    # -----------------------------------------------------------------------------

    def __process_entity_record(
            self,
            record: PublishEntityQueueItem
    ) -> None:
        """Consume queue record with entity updates info"""

        for exchange in self.__exchanges:
            exchange.publish(record.routing_key.value, record.content)

    # -----------------------------------------------------------------------------

    def __load(
            self
    ) -> None:
        # Reset exchanges configuration
        self.__exchanges = set()

        # Process all configured exchanges
        for exchange_settings in self.__settings.all():
            exchange_classname = exchange_settings.get("class")

            if exchange_classname is None:
                log.error(
                    "Classname for configured exchanges: {} is not configured"
                    .format(exchange_settings.get("type"))
                )

                continue

            try:
                # Try to import exchanges class
                exchange_class = LibrariesUtils.check_and_import_exchange(exchange_classname)

                if exchange_class is not None:
                    exchange_module: ExchangeInterface = exchange_class(
                        exchange_settings,
                        self
                    )

                    self.__exchanges.add(exchange_module)

            except Exception as e:
                log.error("Error on loading exchanges:")
                log.exception(e)


#
# Data exchanges interface
#
# @package        FastyBird:MiniServer!
# @subpackage     Exchange
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class ExchangeInterface(ABC):
    __raw_config: dict

    @abstractmethod
    def __init__(self, config: dict) -> None:

        self.__raw_config = config

    # -----------------------------------------------------------------------------

    @abstractmethod
    def close(
            self
    ) -> None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def publish(
            self,
            routing_key: str,
            data: dict
    ) -> None:
        pass
