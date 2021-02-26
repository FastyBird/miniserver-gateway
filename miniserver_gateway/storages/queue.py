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
from miniserver_gateway.utils.properties import PropertiesUtils


#
# Save property value queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Storage
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class SavePropertyValueQueueItem(ABC):
    __item: DevicePropertyItem or ChannelPropertyItem
    __value: bool or int or float or str or None

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        item: DevicePropertyItem or ChannelPropertyItem,
        value: bool or int or float or str or None,
    ) -> None:
        self.__item = item

        # Normalize value to property configuration
        self.__value = PropertiesUtils.normalize_value(item, value)

    # -----------------------------------------------------------------------------

    @property
    def item(self) -> DevicePropertyItem or ChannelPropertyItem:
        return self.__item

    # -----------------------------------------------------------------------------

    @property
    def value(self) -> bool or int or float or str or None:
        """Normalized property value"""
        return self.__value


#
# Save property expected value queue item
#
# @package        FastyBird:MiniServer!
# @subpackage     Storage
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class SavePropertyExpectedValueQueueItem(ABC):
    __item: DevicePropertyItem or ChannelPropertyItem
    __expected_value: bool or int or float or str or None

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        item: DevicePropertyItem or ChannelPropertyItem,
        expected_value: bool or int or float or str or None,
    ) -> None:
        self.__item = item

        # Normalize value to property configuration
        self.__expected_value = PropertiesUtils.normalize_value(item, expected_value)

    # -----------------------------------------------------------------------------

    @property
    def item(self) -> DevicePropertyItem or ChannelPropertyItem:
        return self.__item

    # -----------------------------------------------------------------------------

    @property
    def expected_value(self) -> bool or int or float or str or None:
        """Normalized property value"""
        return self.__expected_value
