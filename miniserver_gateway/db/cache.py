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
import uuid
from abc import abstractmethod
from pony.orm import core as orm
from typing import Dict, Set, Tuple

# App libs
from miniserver_gateway.db.models import DevicePropertyEntity, ChannelPropertyEntity
from miniserver_gateway.db.types import DataType


class PropertyItem:
    __id: uuid.UUID
    __key: str
    __identifier: str
    __settable: bool
    __queryable: bool
    __data_type: DataType or None
    __unit: str or None
    __format: str or None

    __device_id: uuid.UUID

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        property_id: uuid.UUID,
        property_key: str,
        property_identifier: str,
        property_settable: bool,
        property_queryable: bool,
        property_data_type: DataType or None,
        property_unit: str or None,
        property_format: str or None,
        device_id: uuid.UUID,
    ) -> None:
        self.__id = property_id
        self.__key = property_key
        self.__identifier = property_identifier
        self.__settable = property_settable
        self.__queryable = property_queryable
        self.__data_type = property_data_type
        self.__unit = property_unit
        self.__format = property_format

        self.__device_id = device_id

    # -----------------------------------------------------------------------------

    @property
    def device(self) -> uuid.UUID:
        return self.__device_id

    # -----------------------------------------------------------------------------

    @property
    def property_id(self) -> uuid.UUID:
        return self.__id

    # -----------------------------------------------------------------------------

    @property
    def key(self) -> str:
        return self.__key

    # -----------------------------------------------------------------------------

    @property
    def identifier(self) -> str:
        return self.__identifier

    # -----------------------------------------------------------------------------

    @property
    def settable(self) -> bool:
        return self.__settable

    # -----------------------------------------------------------------------------

    @property
    def queryable(self) -> bool:
        return self.__queryable

    # -----------------------------------------------------------------------------

    @property
    def data_type(self) -> DataType or None:
        return self.__data_type

    # -----------------------------------------------------------------------------

    @property
    def unit(self) -> str or None:
        return self.__unit

    # -----------------------------------------------------------------------------

    @property
    def format(self) -> str or None:
        return self.__format

    # -----------------------------------------------------------------------------

    def get_format(self) -> Tuple[int, int] or Tuple[float, float] or Set[str]:
        if self.__format is None:
            return None

        if self.__data_type is not None:
            if self.__data_type == DataType.DATA_TYPE_INT:
                min_value, max_value, *rest = self.__format.split(":") + [None, None]

                if min_value is not None and max_value is not None and int(min_value) <= int(max_value):
                    return int(min_value), int(max_value)

            elif self.__data_type == DataType.DATA_TYPE_FLOAT:
                min_value, max_value, *rest = self.__format.split(":") + [None, None]

                if min_value is not None and max_value is not None and float(min_value) <= float(max_value):
                    return float(min_value), float(max_value)

            elif self.__data_type == DataType.DATA_TYPE_ENUM:
                return set([x.strip() for x in self.__format.split(",")])

        return None

    # -----------------------------------------------------------------------------

    def to_array(self) -> Dict[str, str or int or bool or None]:
        if isinstance(self.data_type, DataType):
            data_type = self.data_type.value

        elif self.data_type is None:
            data_type = None

        else:
            data_type = self.data_type

        return {
            "id": self.property_id.__str__(),
            "key": self.key,
            "identifier": self.identifier,
            "settable": self.settable,
            "queryable": self.queryable,
            "data_type": data_type,
            "unit": self.unit,
            "format": self.format,
        }


class DevicePropertyItem(PropertyItem):
    pass


class ChannelPropertyItem(PropertyItem):
    __channel_id: uuid.UUID

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        property_id: uuid.UUID,
        property_key: str,
        property_identifier: str,
        property_settable: bool,
        property_queryable: bool,
        property_data_type: DataType or None,
        property_unit: str or None,
        property_format: str or None,
        device_id: uuid.UUID,
        channel_id: uuid.UUID,
    ) -> None:
        super().__init__(
            property_id,
            property_key,
            property_identifier,
            property_settable,
            property_queryable,
            property_data_type,
            property_unit,
            property_format,
            device_id,
        )

        self.__channel_id = channel_id

    # -----------------------------------------------------------------------------

    def channel(self) -> uuid.UUID:
        return self.__channel_id


class PropertiesRepository:
    _cache: Dict[str, ChannelPropertyItem or DevicePropertyItem] or None = None

    # -----------------------------------------------------------------------------

    def get_property_by_id(self, property_id: uuid.UUID) -> DevicePropertyItem or ChannelPropertyItem or None:
        if self._cache is None:
            self.initialize()

        try:
            if property_id.__str__() in self._cache:
                return self._cache[property_id.__str__()]

        except TypeError:
            pass

        return None

    # -----------------------------------------------------------------------------

    def get_property_by_key(self, property_key: str) -> DevicePropertyItem or ChannelPropertyItem or None:
        if self._cache is None:
            self.initialize()

        try:
            for record in self._cache.values():
                if record.key == property_key:
                    return record

        except TypeError:
            pass

        return None

    # -----------------------------------------------------------------------------

    def clear_cache(self) -> None:
        self._cache = None

    # -----------------------------------------------------------------------------

    @abstractmethod
    def initialize(self) -> None:
        pass


class DevicesPropertiesCache(PropertiesRepository):
    @orm.db_session
    def initialize(self) -> None:
        data: dict = {}

        for entity in DevicePropertyEntity.select():
            data[entity.property_id.__str__()] = DevicePropertyItem(
                property_id=entity.property_id,
                property_identifier=entity.identifier,
                property_key=entity.key,
                property_settable=entity.settable,
                property_queryable=entity.queryable,
                property_data_type=entity.data_type,
                property_format=entity.format,
                property_unit=entity.unit,
                device_id=entity.device.device_id,
            )

        self._cache = data


class ChannelsPropertiesCache(PropertiesRepository):
    @orm.db_session
    def initialize(self) -> None:
        data: dict = {}

        for entity in ChannelPropertyEntity.select():
            data[entity.property_id.__str__()] = ChannelPropertyItem(
                property_id=entity.property_id,
                property_identifier=entity.identifier,
                property_key=entity.key,
                property_settable=entity.settable,
                property_queryable=entity.queryable,
                property_data_type=entity.data_type,
                property_format=entity.format,
                property_unit=entity.unit,
                device_id=entity.channel.device.device_id,
                channel_id=entity.channel.channel_id,
            )

        self._cache = data


device_property_cache = DevicesPropertiesCache()

channel_property_cache = ChannelsPropertiesCache()
