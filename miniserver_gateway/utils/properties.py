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

# App libs
from miniserver_gateway.db.cache import DevicePropertyItem, ChannelPropertyItem
from miniserver_gateway.db.types import DataType


#
# Properties utils
#
# @package        FastyBird:MiniServer!
# @subpackage     Utils
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class PropertiesUtils:

    @staticmethod
    def normalize_value(
            item: DevicePropertyItem or ChannelPropertyItem,
            value: int or float or str or bool or None
    ) -> int or float or str or bool or None:
        if value is None:
            return None

        if item.data_type is not None:
            if item.data_type == DataType.DATA_TYPE_INT:
                return int(value)

            elif item.data_type == DataType.DATA_TYPE_FLOAT:
                return float(value)

            elif item.data_type == DataType.DATA_TYPE_STRING:
                return str(value)

            elif item.data_type == DataType.DATA_TYPE_BOOLEAN:
                value = str(value)

                return value.lower() in ["true", "1", "t", "y", "yes", "on"]

            elif item.data_type == DataType.DATA_TYPE_ENUM:
                if item.get_format() is not None and len(item.get_format()) > 0:
                    if str(value) in item.get_format():
                        return str(value)

                    else:
                        return None

        return value
