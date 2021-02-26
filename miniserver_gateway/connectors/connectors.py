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
import uuid
from abc import ABC, abstractmethod
from pony.orm import core as orm
from queue import Queue, Full as QueueFull
from threading import Thread
from typing import Dict, List, Set

# App libs
from miniserver_gateway.connectors.events import ConnectorPropertyValueEvent
from miniserver_gateway.connectors.queue import (
    CreateOrUpdateDeviceQueueItem,
    CreateOrUpdateDeviceConfigurationQueueItem,
    DeleteDeviceConfigurationQueueItem,
    CreateOrUpdateChannelPropertyQueueItem,
    DeleteChannelPropertyQueueItem,
    UpdatePropertyExpectedQueueItem,
    CreateOrUpdateChannelConfigurationQueueItem,
    DeleteChannelConfigurationQueueItem,
)
from miniserver_gateway.constants import LOG_LEVEL
from miniserver_gateway.db.cache import (
    device_property_cache,
    channel_property_cache,
    DevicePropertyItem,
    ChannelPropertyItem,
)
from miniserver_gateway.db.models import (
    ConnectorEntity,
    DeviceEntity,
    DeviceConnectorEntity,
    DeviceConfigurationEntity,
    ChannelEntity,
    ChannelPropertyEntity,
    ChannelConfigurationEntity,
)
from miniserver_gateway.db.types import DeviceStates, DataType
from miniserver_gateway.db.utils import EntityKeyHash
from miniserver_gateway.events.dispatcher import app_dispatcher
from miniserver_gateway.exceptions.invalid_argument import InvalidArgumentException
from miniserver_gateway.storages.events import StoragePropertyStoredEvent
from miniserver_gateway.triggers.events import TriggerActionFiredEvent
from miniserver_gateway.utils.libraries import LibrariesUtils
from miniserver_gateway.utils.properties import PropertiesUtils

logging.basicConfig(level=LOG_LEVEL)
log = logging.getLogger("connectors")


#
# Connectors container settings
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class ConnectorsSettings:
    __connectors: List[Dict[str, str]] = {}

    # -----------------------------------------------------------------------------

    def __init__(self, config: List[Dict[str, str]]) -> None:
        self.__connectors = config

    # -----------------------------------------------------------------------------

    def get_class_by_type(self, connector_type: str) -> str or None:
        for connector in self.__connectors:
            if connector.get("type") == connector_type:
                return connector.get("class")

        return None


#
# Connectors container
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class Connectors(Thread):
    __stopped: bool = False

    __settings: ConnectorsSettings

    __connectors: Set["ConnectorInterface"] = set()
    __queue: Queue

    __SHUTDOWN_WAITING_DELAY: int = 3.0

    # -----------------------------------------------------------------------------

    def __init__(self, config: List[Dict[str, str]]) -> None:
        super().__init__()

        self.__settings = ConnectorsSettings(config)

        app_dispatcher.add_listener(
            StoragePropertyStoredEvent.EVENT_NAME, self.__publish_storage_value_event
        )
        app_dispatcher.add_listener(
            TriggerActionFiredEvent.EVENT_NAME, self.__publish_trigger_value_event
        )

        # Queue for consuming incoming data from connectors
        self.__queue = Queue(maxsize=1000)

        # Process gateway connectors
        self.__load()

        # Threading config...
        self.setDaemon(True)
        self.setName("Connectors thread")

    # -----------------------------------------------------------------------------

    def run(self) -> None:
        self.__stopped = False

        # All records have to be processed before thread is closed
        while True:
            if not self.__queue.empty():
                record = self.__queue.get()

                if isinstance(record, CreateOrUpdateDeviceQueueItem):
                    self.__process_device_record(record)

                elif isinstance(
                    record, CreateOrUpdateDeviceConfigurationQueueItem
                ) or isinstance(record, DeleteDeviceConfigurationQueueItem):
                    self.__process_device_configuration_record(record)

                elif isinstance(
                    record, CreateOrUpdateChannelPropertyQueueItem
                ) or isinstance(record, DeleteChannelPropertyQueueItem):
                    self.__process_channel_property_record(record)

                elif isinstance(record, UpdatePropertyExpectedQueueItem):
                    self.__process_property_expected_record(record)

                elif isinstance(
                    record, CreateOrUpdateChannelConfigurationQueueItem
                ) or isinstance(record, DeleteChannelConfigurationQueueItem):
                    self.__process_channel_configuration_record(record)

            if self.__stopped and self.__queue.empty():
                break

            time.sleep(0.001)

    # -----------------------------------------------------------------------------

    def open(self) -> None:
        # Start main thread
        self.start()

        for connector in self.__connectors:
            try:
                connector.open()

            except Exception as e:
                log.exception(e)

                connector.close()

    # -----------------------------------------------------------------------------

    def close(self) -> None:
        # Process all registered connectors...
        for connector in self.__connectors:
            try:
                # ...and send terminate signal to them
                connector.close()

            except Exception as e:
                log.exception(e)

        now: float = time.time()

        waiting_for_closing: bool = True

        # Wait until all connectors are fully terminated
        while waiting_for_closing and time.time() - now < self.__SHUTDOWN_WAITING_DELAY:
            one_alive: bool = False

            for connector in self.__connectors:
                if connector.is_alive() is True:
                    one_alive = True

            if not one_alive:
                waiting_for_closing = False

        self.__stopped = True

    # -----------------------------------------------------------------------------

    def add_or_edit_device(
        self,
        connector_id: uuid.UUID,
        device_id: uuid.UUID,
        identifier: str,
        state: DeviceStates,
        **kwargs
    ) -> None:
        try:
            self.__queue.put(
                CreateOrUpdateDeviceQueueItem(
                    connector_id=connector_id,
                    device_id=device_id,
                    identifier=identifier,
                    state=state,
                    **kwargs
                )
            )

        except QueueFull:
            log.error(
                "Connectors processing queue is full. New messages could not be added"
            )

    # -----------------------------------------------------------------------------

    def add_or_edit_device_configuration(
        self,
        device_id: uuid.UUID,
        configuration_id: uuid.UUID,
        configuration_identifier: str,
        data_type: DataType,
        **kwargs
    ) -> None:
        try:
            self.__queue.put(
                CreateOrUpdateDeviceConfigurationQueueItem(
                    device_id=device_id,
                    configuration_id=configuration_id,
                    configuration_identifier=configuration_identifier,
                    data_type=data_type,
                    **kwargs
                )
            )

        except QueueFull:
            log.error(
                "Connectors processing queue is full. New messages could not be added"
            )

    # -----------------------------------------------------------------------------

    def delete_device_configuration(self, configuration_id: uuid.UUID) -> None:
        try:
            self.__queue.put(
                DeleteDeviceConfigurationQueueItem(configuration_id=configuration_id)
            )

        except QueueFull:
            log.error(
                "Connectors processing queue is full. New messages could not be added"
            )

    # -----------------------------------------------------------------------------

    def add_or_edit_channel_property(
        self,
        device_id: uuid.UUID,
        channel_id: uuid.UUID,
        channel_identifier: str,
        property_id: uuid.UUID,
        property_identifier: str,
        **kwargs
    ) -> None:
        try:
            self.__queue.put(
                CreateOrUpdateChannelPropertyQueueItem(
                    device_id=device_id,
                    channel_id=channel_id,
                    channel_identifier=channel_identifier,
                    property_id=property_id,
                    property_identifier=property_identifier,
                    **kwargs
                )
            )

        except QueueFull:
            log.error(
                "Connectors processing queue is full. New messages could not be added"
            )

    # -----------------------------------------------------------------------------

    def delete_channel_property(self, property_id: uuid.UUID) -> None:
        try:
            self.__queue.put(DeleteChannelPropertyQueueItem(property_id=property_id))

        except QueueFull:
            log.error(
                "Connectors processing queue is full. New messages could not be added"
            )

    # -----------------------------------------------------------------------------

    def add_or_edit_channel_configuration(
        self,
        device_id: uuid.UUID,
        channel_id: uuid.UUID,
        configuration_id: uuid.UUID,
        configuration_identifier: str,
        data_type: DataType,
        **kwargs
    ) -> None:
        try:
            self.__queue.put(
                CreateOrUpdateChannelConfigurationQueueItem(
                    device_id=device_id,
                    channel_id=channel_id,
                    configuration_id=configuration_id,
                    configuration_identifier=configuration_identifier,
                    data_type=data_type,
                    **kwargs
                )
            )

        except QueueFull:
            log.error(
                "Connectors processing queue is full. New messages could not be added"
            )

    # -----------------------------------------------------------------------------

    def delete_channel_configuration(self, configuration_id: uuid.UUID) -> None:
        try:
            self.__queue.put(
                DeleteChannelConfigurationQueueItem(configuration_id=configuration_id)
            )

        except QueueFull:
            log.error(
                "Connectors processing queue is full. New messages could not be added"
            )

    # -----------------------------------------------------------------------------

    @staticmethod
    def send_device_property_to_storage(
        property_id: uuid.UUID,
        actual_value: bool or int or float or str or None,
        previous_value: bool or int or float or str or None = None,
    ) -> None:
        device_property = device_property_cache.get_property_by_id(property_id)

        if device_property is not None:
            app_dispatcher.dispatch(
                ConnectorPropertyValueEvent.EVENT_NAME,
                ConnectorPropertyValueEvent(
                    device_property,
                    PropertiesUtils.normalize_value(device_property, actual_value),
                    PropertiesUtils.normalize_value(device_property, previous_value),
                ),
            )

        else:
            log.warning(
                "Device property: {} was not found in registry".format(
                    property_id.__str__()
                )
            )

    # -----------------------------------------------------------------------------

    @staticmethod
    def send_channel_property_to_storage(
        property_id: uuid.UUID,
        actual_value: bool or int or float or str or None,
        previous_value: bool or int or float or str or None = None,
    ) -> None:
        channel_property = channel_property_cache.get_property_by_id(property_id)

        if channel_property is not None:
            app_dispatcher.dispatch(
                ConnectorPropertyValueEvent.EVENT_NAME,
                ConnectorPropertyValueEvent(
                    channel_property,
                    PropertiesUtils.normalize_value(channel_property, actual_value),
                    PropertiesUtils.normalize_value(channel_property, previous_value),
                ),
            )

        else:
            log.warning(
                "Channel property: {} was not found in registry".format(
                    property_id.__str__()
                )
            )

    # -----------------------------------------------------------------------------

    def __publish_storage_value_event(self, event: StoragePropertyStoredEvent) -> None:
        # Process only messages where i expected value
        if event.expected_value is None:
            return

        self.__publish_value_event(event.record, event.expected_value)

    # -----------------------------------------------------------------------------

    def __publish_trigger_value_event(self, event: TriggerActionFiredEvent) -> None:
        self.__publish_value_event(event.record, event.expected_value)

    # -----------------------------------------------------------------------------

    def __publish_value_event(
        self,
        item: DevicePropertyItem or ChannelPropertyItem,
        value: str or int or float or bool,
    ) -> None:
        try:
            self.__queue.put(UpdatePropertyExpectedQueueItem(item=item, expected=value))

        except QueueFull:
            log.error(
                "Connectors processing queue is full. New messages could not be added"
            )

    # -----------------------------------------------------------------------------

    @orm.db_session
    def __load(self) -> None:
        # Reset connectors configuration
        self.__connectors = set()

        # Process all configured connectors
        for connector in ConnectorEntity.select():
            connector_classname = self.__settings.get_class_by_type(connector.type)

            if connector_classname is None:
                log.error(
                    "Classname for configured connector: {} is not configured".format(
                        connector.type
                    )
                )
                continue

            try:
                # Try to import connector class
                connector_class = LibrariesUtils.check_and_import_connector(
                    connector.type, connector_classname
                )

                connector_module: ConnectorInterface = connector_class(self, connector)

                self.__connectors.add(connector_module)

            except Exception as e:
                log.error("Error on loading connector:")
                log.exception(e)

    # -----------------------------------------------------------------------------

    @orm.db_session
    def __process_device_record(self, record: CreateOrUpdateDeviceQueueItem) -> None:
        device: DeviceEntity or None = DeviceEntity.get(device_id=record.device_id)

        if device is None:
            connector: ConnectorEntity = ConnectorEntity.get(
                connector_id=record.connector_id
            )

            device: DeviceEntity = DeviceEntity(
                device_id=record.device_id,
                identifier=record.identifier,
                key=EntityKeyHash.encode(int(time.time_ns() / 1000)),
                state=record.state,
                enabled=True,
            )

            connector_params: dict or None = None

            if "connector_params" in record.attributes.keys():
                connector_params = record.attributes.get("connector_params")

            DeviceConnectorEntity(
                device=device, connector=connector, params=connector_params
            )

        else:
            if "connector_params" in record.attributes.keys():
                device_connector: DeviceConnectorEntity = DeviceConnectorEntity.get(
                    device=device
                )
                device_connector.params = record.attributes.get("connector_params")

        self.__update_device_entity(device, **record.attributes)

    # -----------------------------------------------------------------------------

    @orm.db_session
    def __process_device_configuration_record(
        self,
        record: CreateOrUpdateDeviceConfigurationQueueItem
        or DeleteDeviceConfigurationQueueItem,
    ) -> None:
        if isinstance(record, CreateOrUpdateDeviceConfigurationQueueItem):
            device: DeviceEntity or None = DeviceEntity.get(device_id=record.device_id)

            if device is not None:
                device_configuration: DeviceConfigurationEntity or None = (
                    DeviceConfigurationEntity.get(
                        configuration_id=record.configuration_id
                    )
                )

                if device_configuration is None:
                    device_configuration: DeviceConfigurationEntity = (
                        DeviceConfigurationEntity(
                            device=device,
                            configuration_id=record.configuration_id,
                            key=EntityKeyHash.encode(int(time.time_ns() / 1000)),
                            identifier=record.configuration_identifier,
                            data_type=record.data_type,
                        )
                    )

                self.__update_channel_configuration_entity(
                    device_configuration, **record.attributes
                )

        elif isinstance(record, DeleteDeviceConfigurationQueueItem):
            device_configuration: DeviceConfigurationEntity = (
                DeviceConfigurationEntity.get(id=record.configuration_id)
            )

            if device_configuration is not None:
                device_configuration.delete()

        else:
            raise InvalidArgumentException("Provided queue item is not valid")

    # -----------------------------------------------------------------------------

    @orm.db_session
    def __process_channel_property_record(
        self,
        record: CreateOrUpdateChannelPropertyQueueItem
        or DeleteChannelPropertyQueueItem,
    ) -> None:
        if isinstance(record, CreateOrUpdateChannelPropertyQueueItem):
            device: DeviceEntity = DeviceEntity.get(device_id=record.device_id)

            if device is not None:
                channel: ChannelEntity = ChannelEntity.get(
                    channel_id=record.channel_id, device=device
                )

                if channel is None:
                    channel: ChannelEntity = ChannelEntity(
                        channel_id=record.channel_id,
                        key=EntityKeyHash.encode(int(time.time_ns() / 1000)),
                        device=device,
                        identifier=record.channel_identifier,
                    )

                channel_property: ChannelPropertyEntity = ChannelPropertyEntity.get(
                    property_id=record.property_id
                )

                if channel_property is None:
                    channel_property: ChannelPropertyEntity = ChannelPropertyEntity(
                        property_id=record.property_id,
                        key=record.key,
                        channel=channel,
                        identifier=record.property_identifier,
                        settable=record.attributes.get("settable", False),
                        queryable=record.attributes.get("queryable", False),
                    )

                self.__update_channel_property_entity(
                    channel_property, **record.attributes
                )

                # Refresh repository cache
                channel_property_cache.clear_cache()

        elif isinstance(record, DeleteChannelPropertyQueueItem):
            channel_property: ChannelPropertyEntity = ChannelPropertyEntity.get(
                property_id=record.property_id
            )

            if channel_property is not None:
                channel_property.delete()

                # Refresh repository cache
                channel_property_cache.clear_cache()

        else:
            raise InvalidArgumentException("Provided queue item is not valid")

    # -----------------------------------------------------------------------------

    def __process_property_expected_record(
        self, record: UpdatePropertyExpectedQueueItem
    ) -> None:
        expected = record.expected_value

        if (
            record.item.data_type != DataType.DATA_TYPE_BOOLEAN
            or record.expected_value != "toggle"
        ):
            expected = PropertiesUtils.normalize_value(
                record.item, record.expected_value
            )

        # Process all registered connectors...
        for connector in self.__connectors:
            # ...and send value update to them
            connector.publish(record.item.property_id, expected)

    # -----------------------------------------------------------------------------

    @orm.db_session
    def __process_channel_configuration_record(
        self,
        record: CreateOrUpdateChannelConfigurationQueueItem
        or DeleteChannelConfigurationQueueItem,
    ) -> None:
        if isinstance(record, CreateOrUpdateChannelConfigurationQueueItem):
            device: DeviceEntity or None = DeviceEntity.get(device_id=record.device_id)

            if device is not None:
                channel: ChannelEntity = ChannelEntity.get(
                    channel_id=record.channel_id, device=device
                )

                if channel is None:
                    log.warning(
                        "Channel with id: {} is not configured yet".format(
                            record.channel_id.__str__()
                        )
                    )

                    return

                channel_configuration: ChannelConfigurationEntity or None = (
                    ChannelConfigurationEntity.get(
                        configuration_id=record.configuration_id
                    )
                )

                if channel_configuration is None:
                    channel_configuration: ChannelConfigurationEntity = (
                        ChannelConfigurationEntity(
                            channel=channel,
                            configuration_id=record.configuration_id,
                            key=EntityKeyHash.encode(int(time.time_ns() / 1000)),
                            identifier=record.configuration_identifier,
                            data_type=record.data_type,
                        )
                    )

                self.__update_channel_configuration_entity(
                    channel_configuration, **record.attributes
                )

        elif isinstance(record, DeleteChannelConfigurationQueueItem):
            channel_configuration: ChannelConfigurationEntity = (
                ChannelConfigurationEntity.get(id=record.configuration_id)
            )

            if channel_configuration is not None:
                channel_configuration.delete()

        else:
            raise InvalidArgumentException("Provided queue item is not valid")

    # -----------------------------------------------------------------------------

    def __update_device_entity(self, device: DeviceEntity, **kwargs) -> bool:
        available_attributes: List[str] = [
            "state",
            "hardware_manufacturer",
            "hardware_model",
            "hardware_version",
            "mac_address",
            "firmware_manufacturer",
            "firmware_version",
        ]

        return self.__update_entity(device, available_attributes, **kwargs)

    # -----------------------------------------------------------------------------

    def __update_channel_property_entity(
        self, channel_property: ChannelPropertyEntity, **kwargs
    ) -> bool:
        available_attributes: List[str] = [
            "settable",
            "queryable",
            "data_type",
            "unit",
            "format",
        ]

        return self.__update_entity(channel_property, available_attributes, **kwargs)

    # -----------------------------------------------------------------------------

    def __update_device_configuration_entity(
        self, channel_configuration: DeviceConfigurationEntity, **kwargs
    ) -> bool:
        available_attributes: List[str] = [
            "default",
            "value",
        ]

        return self.__update_entity(
            channel_configuration, available_attributes, **kwargs
        )

    # -----------------------------------------------------------------------------

    def __update_channel_configuration_entity(
        self, channel_configuration: ChannelConfigurationEntity, **kwargs
    ) -> bool:
        available_attributes: List[str] = [
            "default",
            "value",
        ]

        return self.__update_entity(
            channel_configuration, available_attributes, **kwargs
        )

    # -----------------------------------------------------------------------------

    @staticmethod
    def __update_entity(
        entity: orm.Entity, available_attributes: List[str], **kwargs
    ) -> bool:
        update_values: Dict[str, str or int or bool] = {}

        # Parse all provided keys & values
        for key, value in kwargs.items():
            if key in available_attributes and getattr(entity, key) != value:
                update_values[key] = value

        if len(update_values) > 0:
            # Update entity values
            entity.set(**update_values)

            return True

        return False


#
# Connector interface
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class ConnectorInterface(ABC, Thread):
    @abstractmethod
    def open(self) -> None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def close(self) -> None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def publish(
        self, property_id: uuid.UUID, expected: bool or int or float or str or None
    ) -> str:
        pass
