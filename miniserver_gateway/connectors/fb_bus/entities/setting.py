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
from abc import ABC
import uuid

# App libs
from miniserver_gateway.connectors.fb_bus.types.types import DataTypes, RegistersTypes


#
# Device or register setting entity
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class SettingEntity(ABC):
    __id: uuid.UUID  # Register index in registry
    __device_id: uuid.UUID
    __name: str or None = None
    __data_type: DataTypes
    __size: int = 0
    __value: int or float or bool or None = None
    __address: int

    # -----------------------------------------------------------------------------

    def __init__(self, index: uuid.UUID, device_id: uuid.UUID, setting_address: int) -> None:
        self.__id = index
        self.__device_id = device_id
        self.__address = setting_address

        self.set_data_type(DataTypes(DataTypes.FB_DATA_TYPE_UNKNOWN))

    # -----------------------------------------------------------------------------

    def get_id(self) -> uuid.UUID:
        return self.__id

    # -----------------------------------------------------------------------------

    def get_device_id(self) -> uuid.UUID:
        return self.__device_id

    # -----------------------------------------------------------------------------

    def get_address(self) -> int:
        return self.__address

    # -----------------------------------------------------------------------------

    def set_name(self, name: str) -> None:
        self.__name = name

    # -----------------------------------------------------------------------------

    def get_name(self) -> str or None:
        return self.__name

    # -----------------------------------------------------------------------------

    def get_data_type(self) -> DataTypes:
        return self.__data_type

    # -----------------------------------------------------------------------------

    def set_data_type(self, data_type: DataTypes) -> None:
        if data_type == DataTypes.FB_DATA_TYPE_UINT8 or data_type == DataTypes.FB_DATA_TYPE_INT8:
            self.__size = 1

        elif data_type == DataTypes.FB_DATA_TYPE_UINT16 or data_type == DataTypes.FB_DATA_TYPE_INT16:
            self.__size = 2

        elif (
            data_type == DataTypes.FB_DATA_TYPE_UINT32
            or data_type == DataTypes.FB_DATA_TYPE_INT32
            or data_type == DataTypes.FB_DATA_TYPE_FLOAT32
        ):
            self.__size = 4

        elif data_type == DataTypes.FB_DATA_TYPE_BOOL:
            self.__size = 1

        elif data_type == DataTypes.FB_DATA_TYPE_UNKNOWN:
            self.__size = 0

        self.__data_type = data_type

    # -----------------------------------------------------------------------------

    def get_value(self) -> int or float or bool or None:
        return self.__value

    # -----------------------------------------------------------------------------

    def set_value(self, value: int or float or bool) -> None:
        self.__value = value


#
# Device setting entity
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class DeviceSettingEntity(SettingEntity):
    pass


#
# Register setting entity
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class RegisterSettingEntity(SettingEntity):
    __register_address: int or None = None
    __register_type: RegistersTypes or None = None

    # -----------------------------------------------------------------------------

    def set_register(self, register_address: int, register_type: RegistersTypes) -> None:
        self.__register_address = register_address
        self.__register_type = register_type

    # -----------------------------------------------------------------------------

    def get_register_address(self) -> int or None:
        return self.__register_address

    # -----------------------------------------------------------------------------

    def get_register_type(self) -> RegistersTypes or None:
        return self.__register_type
