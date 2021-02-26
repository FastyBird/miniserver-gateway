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


#
# Storage has saved property to storage
#
# @package        FastyBird:MiniServer!
# @subpackage     Storage
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class StoragePropertyStoredEvent(ABC, Event):
    __record: DevicePropertyItem or ChannelPropertyItem
    __value: str or int or float or bool or None
    __expected_value: str or int or float or bool or None
    __pending: bool

    EVENT_NAME: str = "storages.propertySaved"

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        record: DevicePropertyItem or ChannelPropertyItem,
        value: str or int or float or bool or None = None,
        expected_value: str or int or float or bool or None = None,
        pending: bool = False,
    ) -> None:
        self.__record = record
        self.__value = value
        self.__expected_value = expected_value
        self.__pending = pending

    # -----------------------------------------------------------------------------

    @property
    def record(self) -> DevicePropertyItem or ChannelPropertyItem:
        return self.__record

    # -----------------------------------------------------------------------------

    @property
    def value(self) -> str or int or float or bool or None:
        return self.__value

    # -----------------------------------------------------------------------------

    @property
    def expected_value(self) -> str or int or float or bool or None:
        return self.__expected_value

    # -----------------------------------------------------------------------------

    @property
    def is_pending(self) -> bool:
        return self.__pending
