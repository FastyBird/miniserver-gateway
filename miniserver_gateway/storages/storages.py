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
from abc import ABC, abstractmethod
from queue import Queue, Full as QueueFull
from threading import Thread
from typing import Dict, List, Set

# App libs
from miniserver_gateway.connectors.events import ConnectorPropertyValueEvent
from miniserver_gateway.constants import LOG_LEVEL
from miniserver_gateway.db.cache import DevicePropertyItem, ChannelPropertyItem
from miniserver_gateway.events.dispatcher import app_dispatcher
from miniserver_gateway.exchanges.events import ExchangePropertyExpectedValueEvent
from miniserver_gateway.storages.events import StoragePropertyStoredEvent
from miniserver_gateway.storages.queue import (
    SavePropertyValueQueueItem,
    SavePropertyExpectedValueQueueItem,
)
from miniserver_gateway.utils.libraries import LibrariesUtils

logging.basicConfig(level=LOG_LEVEL)
log = logging.getLogger("storage")


#
# Storages container settings
#
# @package        FastyBird:MiniServer!
# @subpackage     Storage
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class StoragesSettings:
    __storages: List[Dict[str, str]] = {}

    # -----------------------------------------------------------------------------

    def __init__(self, config: List[Dict[str, str]]) -> None:
        self.__storages = config

    # -----------------------------------------------------------------------------

    def all(self) -> List[Dict[str, str]]:
        return self.__storages


#
# Storages container
#
# @package        FastyBird:MiniServer!
# @subpackage     Storage
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class Storages(Thread):
    __stopped: bool = False

    __settings: StoragesSettings

    __primary_storage: "StorageInterface" or None = None
    __storages: Set["StorageInterface"] = set()

    __queue: Queue

    __SHUTDOWN_WAITING_DELAY: int = 3.0

    # -----------------------------------------------------------------------------

    def __init__(self, config: List[Dict[str, str]]) -> None:
        super().__init__()

        self.__settings = StoragesSettings(config)

        app_dispatcher.add_listener(
            ConnectorPropertyValueEvent.EVENT_NAME, self.__store_value_event
        )
        app_dispatcher.add_listener(
            ExchangePropertyExpectedValueEvent.EVENT_NAME,
            self.__store_expected_value_event,
        )

        # Queue for consuming incoming data from connectors
        self.__queue = Queue(maxsize=1000)

        # Process storages services
        self.__load()

        if self.__primary_storage is None:
            log.error("Primary data storage is not configured!!!")

        # Threading config...
        self.setDaemon(True)
        self.setName("Storage thread")
        # ...and starting
        self.start()

    # -----------------------------------------------------------------------------

    def run(self) -> None:
        self.__stopped = False

        # All records have to be processed before thread is closed
        while True:
            if not self.__queue.empty():
                record = self.__queue.get()

                if isinstance(record, SavePropertyValueQueueItem):
                    self.__process_property_value_record(record)

                elif isinstance(record, SavePropertyExpectedValueQueueItem):
                    self.__process_property_expected_value_record(record)

            if self.__stopped and self.__queue.empty():
                break

            time.sleep(0.001)

    # -----------------------------------------------------------------------------

    def close(self) -> None:
        """Stop storage main thread"""

        for storage in self.__storages:
            try:
                # Send terminate cmd to all sub-storages
                storage.close()

            except Exception as e:
                log.exception(e)

        now: float = time.time()

        waiting_for_closing: bool = True

        # Wait until all sub-exchanges are fully terminated
        while waiting_for_closing and time.time() - now < self.__SHUTDOWN_WAITING_DELAY:
            one_alive: bool = False

            for storage in self.__storages:
                if isinstance(storage, Thread) and storage.is_alive() is True:
                    one_alive = True

            if not one_alive:
                waiting_for_closing = False

        self.__stopped = True

    # -----------------------------------------------------------------------------

    def __store_value_event(self, event: ConnectorPropertyValueEvent) -> None:
        try:
            if isinstance(event.record, DevicePropertyItem) or isinstance(
                event.record, ChannelPropertyItem
            ):
                self.__queue.put(
                    SavePropertyValueQueueItem(event.record, event.actual_value)
                )

            else:
                log.warning("Received unknown connectors event")

        except QueueFull:
            log.error(
                "Storage processing queue is full. New messages could not be added"
            )

    # -----------------------------------------------------------------------------

    def __store_expected_value_event(
        self, event: ExchangePropertyExpectedValueEvent
    ) -> None:
        try:
            if isinstance(event.item, DevicePropertyItem):
                self.__queue.put(
                    SavePropertyExpectedValueQueueItem(
                        event.item,
                        event.expected,
                    )
                )

            elif isinstance(event.item, ChannelPropertyItem):
                self.__queue.put(
                    SavePropertyExpectedValueQueueItem(
                        event.item,
                        event.expected,
                    )
                )

            else:
                log.warning("Received unknown exchanges event")

        except QueueFull:
            log.error(
                "Storage processing queue is full. New messages could not be added"
            )

    # -----------------------------------------------------------------------------

    def __process_property_value_record(
        self, record: SavePropertyValueQueueItem
    ) -> None:
        if self.__primary_storage is None:
            return

        if not isinstance(record.item, DevicePropertyItem) and not isinstance(
            record.item, ChannelPropertyItem
        ):
            # Unknown record item
            return

        if self.__primary_storage.write_property_value(record.item, record.value):
            stored_data: StorageItem = self.__primary_storage.read_property_data(
                record.item
            )

            app_dispatcher.dispatch(
                StoragePropertyStoredEvent.EVENT_NAME,
                StoragePropertyStoredEvent(
                    record.item,
                    stored_data.value,
                    stored_data.expected,
                    stored_data.expected,
                ),
            )

    # -----------------------------------------------------------------------------

    def __process_property_expected_value_record(
        self, record: SavePropertyExpectedValueQueueItem
    ) -> None:
        if self.__primary_storage is None:
            return

        if isinstance(record.item, DevicePropertyItem):
            property_item: DevicePropertyItem = record.item

        elif isinstance(record.item, ChannelPropertyItem):
            property_item: ChannelPropertyItem = record.item

        else:
            return

        if self.__primary_storage.write_property_expected(
            property_item, record.expected_value
        ):
            stored_data: StorageItem = self.__primary_storage.read_property_data(
                property_item
            )

            app_dispatcher.dispatch(
                StoragePropertyStoredEvent.EVENT_NAME,
                StoragePropertyStoredEvent(
                    property_item,
                    stored_data.value,
                    stored_data.expected,
                    stored_data.expected,
                ),
            )

    # -----------------------------------------------------------------------------

    def __load(self) -> None:
        # Reset storages configuration
        self.__storages = set()

        # Process all configured storages
        for storage_settings in self.__settings.all():
            storage_classname = storage_settings.get("class")

            if storage_classname is None:
                log.error(
                    "Classname for configured storage: {} is not configured".format(
                        storage_settings.get("type")
                    )
                )
                continue

            try:
                # Try to import storage class
                storage_class = LibrariesUtils.check_and_import_storage(
                    storage_classname
                )

                storage_module: StorageInterface = storage_class(storage_settings)

                if storage_settings.get("primary", False) is True:
                    self.__primary_storage = storage_module

                self.__storages.add(storage_module)

            except Exception as e:
                log.error("Error on loading storage:")
                log.exception(e)


#
# Storage item record
#
# @package        FastyBird:MiniServer!
# @subpackage     Storage
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class StorageItem:
    __value: bool or int or float or str or None
    __expected: bool or int or float or str or None
    __pending: bool

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        value: bool or int or float or str or None,
        expected: bool or int or float or str or None,
        pending: bool,
    ) -> None:
        self.__value = value
        self.__expected = expected
        self.__pending = pending

    # -----------------------------------------------------------------------------

    @property
    def value(self) -> bool or int or float or str or None:
        return self.__value

    # -----------------------------------------------------------------------------

    @property
    def expected(self) -> bool or int or float or str or None:
        return self.__expected

    # -----------------------------------------------------------------------------

    @property
    def is_pending(self) -> bool:
        return self.__pending


#
# Data storages interface
#
# @package        FastyBird:MiniServer!
# @subpackage     Storage
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class StorageInterface(ABC):
    __raw_config: dict

    @abstractmethod
    def __init__(self, config: dict) -> None:
        self.__raw_config = config

    # -----------------------------------------------------------------------------

    @abstractmethod
    def close(self) -> None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def clear_cache(self) -> None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def write_property_value(
        self,
        item: DevicePropertyItem or ChannelPropertyItem,
        value_to_write: int or float or str or bool or None,
    ) -> bool:
        """Write value to storage and return TRUE if value is updated otherwise FALSE"""
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def write_property_expected(
        self,
        item: DevicePropertyItem or ChannelPropertyItem,
        expected_value_to_write: int or float or str or bool or None,
    ) -> bool:
        """Write expected value to storage and return TRUE if expected value is updated otherwise FALSE"""
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def read_property_value(
        self, item: DevicePropertyItem or ChannelPropertyItem
    ) -> int or float or str or bool or None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def read_property_expected(
        self, item: DevicePropertyItem or ChannelPropertyItem
    ) -> int or float or str or bool or None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def read_property_data(
        self, item: DevicePropertyItem or ChannelPropertyItem
    ) -> StorageItem or None:
        pass
