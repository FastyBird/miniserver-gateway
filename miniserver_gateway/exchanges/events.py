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
# Received property message from exchanges event
#
# @package        FastyBird:MiniServer!
# @subpackage     Exchange
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class ExchangePropertyExpectedValueEvent(ABC, Event):
    __record: DevicePropertyItem or ChannelPropertyItem
    __expected: str or int or float or bool

    EVENT_NAME: str = "exchanges.expectedPropertyValue"

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        record: DevicePropertyItem or ChannelPropertyItem,
        expected: str or int or float or bool,
    ) -> None:
        self.__record = record
        self.__expected = expected

    # -----------------------------------------------------------------------------

    @property
    def item(self) -> DevicePropertyItem or ChannelPropertyItem:
        return self.__record

    # -----------------------------------------------------------------------------

    @property
    def expected(self) -> str or int or float or bool:
        return self.__expected
