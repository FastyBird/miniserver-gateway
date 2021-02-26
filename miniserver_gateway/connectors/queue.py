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
import time
import uuid
from abc import ABC
from typing import Dict

# App libs
from miniserver_gateway.db.cache import DevicePropertyItem, ChannelPropertyItem
from miniserver_gateway.db.utils import EntityKeyHash
from miniserver_gateway.db.types import DeviceStates, DataType


class QueueItem(ABC):
    pass


#
# Created or update device queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class CreateOrUpdateDeviceQueueItem(QueueItem):
    __connector_id: uuid.UUID
    __device_id: uuid.UUID
    __identifier: str
    __state: DeviceStates
    __attributes: Dict[str, str or int or float or bool or dict or None]

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        connector_id: uuid.UUID,
        device_id: uuid.UUID,
        identifier: str,
        state: DeviceStates,
        **kwargs
    ) -> None:
        self.__connector_id = connector_id
        self.__device_id = device_id
        self.__identifier = identifier
        self.__state = state

        self.__attributes = kwargs

    # -----------------------------------------------------------------------------

    @property
    def connector_id(self) -> uuid.UUID:
        return self.__connector_id

    # -----------------------------------------------------------------------------

    @property
    def device_id(self) -> uuid.UUID:
        return self.__device_id

    # -----------------------------------------------------------------------------

    @property
    def identifier(self) -> str:
        return self.__identifier

    # -----------------------------------------------------------------------------

    @property
    def state(self) -> DeviceStates:
        return self.__state

    # -----------------------------------------------------------------------------

    @property
    def attributes(self) -> dict:
        return {**self.__attributes, **{"state": self.__state}}


#
# Create or update property queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class CreateOrUpdatePropertyQueueItem(QueueItem):
    __device_id: uuid.UUID
    __property_id: uuid.UUID
    __property_identifier: str
    __attributes: Dict[str, str or int or float or bool or dict or None]

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        device_id: uuid.UUID,
        property_id: uuid.UUID,
        property_identifier: str,
        **kwargs
    ) -> None:
        self.__device_id = device_id
        self.__property_id = property_id
        self.__property_identifier = property_identifier

        self.__attributes = kwargs

    # -----------------------------------------------------------------------------

    @property
    def device_id(self) -> uuid.UUID:
        return self.__device_id

    # -----------------------------------------------------------------------------

    @property
    def property_id(self) -> uuid.UUID:
        return self.__property_id

    # -----------------------------------------------------------------------------

    @property
    def key(self) -> str:
        if "key" in self.__attributes.keys():
            return self.__attributes.get("key")

        return EntityKeyHash.encode(int(time.time_ns() / 1000))

    # -----------------------------------------------------------------------------

    @property
    def property_identifier(self) -> str:
        return self.__property_identifier

    # -----------------------------------------------------------------------------

    @property
    def attributes(self) -> dict:
        return self.__attributes


#
# Create or update channel property queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class CreateOrUpdateDevicePropertyQueueItem(CreateOrUpdatePropertyQueueItem):
    pass


#
# Create or update channel property queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class CreateOrUpdateChannelPropertyQueueItem(CreateOrUpdatePropertyQueueItem):
    __channel_id: uuid.UUID
    __channel_identifier: str

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        device_id: uuid.UUID,
        channel_id: uuid.UUID,
        channel_identifier: str,
        property_id: uuid.UUID,
        property_identifier: str,
        **kwargs
    ) -> None:
        super().__init__(device_id, property_id, property_identifier, **kwargs)

        self.__channel_id = channel_id
        self.__channel_identifier = channel_identifier

    # -----------------------------------------------------------------------------

    @property
    def channel_id(self) -> uuid.UUID:
        return self.__channel_id

    # -----------------------------------------------------------------------------

    @property
    def channel_identifier(self) -> str:
        return self.__channel_identifier


#
# Delete property queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class DeletePropertyQueueItem(QueueItem):
    __property_id: uuid.UUID

    # -----------------------------------------------------------------------------

    def __init__(self, property_id: uuid.UUID) -> None:
        self.__property_id = property_id

    # -----------------------------------------------------------------------------

    @property
    def property_id(self) -> uuid.UUID:
        return self.__property_id


#
# Delete device property queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class DeleteDevicePropertyQueueItem(DeletePropertyQueueItem):
    pass


#
# Delete channel property queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class DeleteChannelPropertyQueueItem(DeletePropertyQueueItem):
    pass


#
# Update property expected queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class UpdatePropertyExpectedQueueItem(QueueItem):
    __item: DevicePropertyItem or ChannelPropertyItem
    __expected: bool or int or float or str or None

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        item: DevicePropertyItem or ChannelPropertyItem,
        expected: bool or int or float or str or None,
    ) -> None:
        self.__item = item
        self.__expected = expected

    # -----------------------------------------------------------------------------

    @property
    def item(self) -> DevicePropertyItem or ChannelPropertyItem:
        return self.__item

    # -----------------------------------------------------------------------------

    @property
    def expected_value(self) -> bool or int or float or str or None:
        return self.__expected


#
# Create or update channel configuration queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class CreateOrUpdateConfigurationQueueItem(QueueItem):
    __device_id: uuid.UUID
    __configuration_id: uuid.UUID
    __configuration_identifier: str
    __data_type: DataType
    __attributes: Dict[str, str or int or float or bool or dict or None]

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        device_id: uuid.UUID,
        configuration_id: uuid.UUID,
        configuration_identifier: str,
        data_type: DataType,
        **kwargs
    ) -> None:
        self.__device_id = device_id
        self.__configuration_id = configuration_id
        self.__configuration_identifier = configuration_identifier
        self.__data_type = data_type

        self.__attributes = kwargs

    # -----------------------------------------------------------------------------

    @property
    def device_id(self) -> uuid.UUID:
        return self.__device_id

    # -----------------------------------------------------------------------------

    @property
    def configuration_id(self) -> uuid.UUID:
        return self.__configuration_id

    # -----------------------------------------------------------------------------

    @property
    def configuration_identifier(self) -> str:
        return self.__configuration_identifier

    # -----------------------------------------------------------------------------

    @property
    def data_type(self) -> DataType:
        return self.__data_type

    # -----------------------------------------------------------------------------

    @property
    def attributes(self) -> dict:
        return self.__attributes


#
# Create or update device configuration queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class CreateOrUpdateDeviceConfigurationQueueItem(CreateOrUpdateConfigurationQueueItem):
    pass


#
# Create or update channel configuration queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class CreateOrUpdateChannelConfigurationQueueItem(CreateOrUpdateConfigurationQueueItem):
    __channel_id: uuid.UUID

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        device_id: uuid.UUID,
        channel_id: uuid.UUID,
        configuration_id: uuid.UUID,
        configuration_identifier: str,
        data_type: DataType,
        **kwargs
    ) -> None:
        super().__init__(
            device_id, configuration_id, configuration_identifier, data_type, **kwargs
        )

        self.__channel_id = channel_id

    # -----------------------------------------------------------------------------

    @property
    def channel_id(self) -> uuid.UUID:
        return self.__channel_id


#
# Delete configuration queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class DeleteConfigurationQueueItem(QueueItem):
    __configuration_id: uuid.UUID

    # -----------------------------------------------------------------------------

    def __init__(self, configuration_id: uuid.UUID) -> None:
        self.__configuration_id = configuration_id

    # -----------------------------------------------------------------------------

    @property
    def configuration_id(self) -> uuid.UUID:
        return self.__configuration_id


#
# Delete device configuration queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class DeleteDeviceConfigurationQueueItem(DeleteConfigurationQueueItem):
    pass


#
# Delete device configuration queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class DeleteChannelConfigurationQueueItem(DeleteConfigurationQueueItem):
    pass
