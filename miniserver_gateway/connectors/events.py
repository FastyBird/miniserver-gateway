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
from abc import ABC
from whistle import Event

# App libs
from miniserver_gateway.db.cache import DevicePropertyItem, ChannelPropertyItem
from miniserver_gateway.types.types import ModulesOrigins


#
# Connector has received property value event
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class ConnectorPropertyValueEvent(ABC, Event):
    __origin: ModulesOrigins
    __record: DevicePropertyItem or ChannelPropertyItem
    __actual_value: str or int or float or bool
    __previous_value: str or int or float or bool or None

    EVENT_NAME: str = "connectors.propertyValue"

    def __init__(
        self,
        origin: ModulesOrigins,
        record: DevicePropertyItem or ChannelPropertyItem,
        actual_value: str or int or float or bool,
        previous_value: str or int or float or bool or None,
    ) -> None:
        self.__origin = origin
        self.__record = record
        self.__actual_value = actual_value
        self.__previous_value = previous_value

    # -----------------------------------------------------------------------------

    @property
    def origin(self) -> ModulesOrigins:
        return self.__origin

    # -----------------------------------------------------------------------------

    @property
    def record(self) -> DevicePropertyItem or ChannelPropertyItem:
        return self.__record

    # -----------------------------------------------------------------------------

    @property
    def actual_value(self) -> str or int or float or bool:
        return self.__actual_value

    # -----------------------------------------------------------------------------

    @property
    def previous_value(self) -> str or int or float or bool:
        return self.__previous_value
