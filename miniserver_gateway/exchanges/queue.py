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

# App libs
from miniserver_gateway.db.cache import DevicePropertyItem, ChannelPropertyItem
from miniserver_gateway.exchanges.types import RoutingKeys
from miniserver_gateway.types.types import ModulesOrigins


#
# Update property value queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Exchange
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class PublishPropertyValueQueueItem(ABC):
    __origin: ModulesOrigins
    __item: DevicePropertyItem or ChannelPropertyItem
    __value: bool or int or float or str or None
    __expected_value: bool or int or float or str or None
    __is_pending: bool

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        origin: ModulesOrigins,
        item: DevicePropertyItem or ChannelPropertyItem,
        value: bool or int or float or str or None,
        expected_value: bool or int or float or str or None,
        is_pending: bool,
    ) -> None:
        self.__origin = origin
        self.__item = item

        self.__value = value
        self.__expected_value = expected_value
        self.__is_pending = is_pending

    # -----------------------------------------------------------------------------

    @property
    def origin(self) -> ModulesOrigins:
        return self.__origin

    # -----------------------------------------------------------------------------

    @property
    def item(self) -> DevicePropertyItem or ChannelPropertyItem:
        return self.__item

    # -----------------------------------------------------------------------------

    @property
    def value(self) -> bool or int or float or str or None:
        return self.__value

    # -----------------------------------------------------------------------------

    @property
    def expected_value(self) -> bool or int or float or str or None:
        return self.__expected_value

    # -----------------------------------------------------------------------------

    @property
    def is_pending(self) -> bool or int or float or str or None:
        return self.__is_pending


#
# Entity changed queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Exchange
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class PublishEntityQueueItem:
    __origin: ModulesOrigins
    __routing_key: RoutingKeys
    __content: dict

    def __init__(self, origin: ModulesOrigins, routing_key: RoutingKeys, content: dict) -> None:
        self.__origin = origin
        self.__routing_key = routing_key
        self.__content = content

    # -----------------------------------------------------------------------------

    @property
    def origin(self) -> ModulesOrigins:
        return self.__origin

    # -----------------------------------------------------------------------------

    @property
    def routing_key(self) -> RoutingKeys:
        return self.__routing_key

    # -----------------------------------------------------------------------------

    @property
    def content(self) -> dict:
        return self.__content
