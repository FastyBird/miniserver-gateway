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
import uuid

# App libs
from miniserver_gateway.connectors.fb_bus.types.types import DataTypes, RegistersTypes


#
# Device register entity
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class RegisterEntity:
    __id: uuid.UUID  # Register index in registry
    __key: str
    __channel_id: uuid.UUID
    __device_id: uuid.UUID
    __type: RegistersTypes
    __data_type: DataTypes
    __size: int = 0
    __value: int or float or bool or None = None
    __address: int

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        index: uuid.UUID,
        key: str,
        channel_id: uuid.UUID,
        device_id: uuid.UUID,
        register_address: int,
        register_type: RegistersTypes,
        register_data_type: DataTypes,
    ) -> None:
        self.__id = index
        self.__key = key
        self.__channel_id = channel_id
        self.__device_id = device_id
        self.__address = register_address
        self.__type = register_type

        self.set_data_type(register_data_type)

    # -----------------------------------------------------------------------------

    def get_id(self) -> uuid.UUID:
        return self.__id

    # -----------------------------------------------------------------------------

    def get_key(self) -> str:
        return self.__key

    # -----------------------------------------------------------------------------

    def get_device_id(self) -> uuid.UUID:
        return self.__device_id

    # -----------------------------------------------------------------------------

    def get_channel_id(self) -> uuid.UUID:
        return self.__channel_id

    # -----------------------------------------------------------------------------

    def get_address(self) -> int:
        return self.__address

    # -----------------------------------------------------------------------------

    def get_type(self) -> RegistersTypes:
        return self.__type

    # -----------------------------------------------------------------------------

    def is_writable(self) -> bool:
        return (
            self.__type == RegistersTypes.FB_REGISTER_DO
            or self.__type == RegistersTypes.FB_REGISTER_AO
        )

    # -----------------------------------------------------------------------------

    def get_data_type(self) -> DataTypes:
        return self.__data_type

    # -----------------------------------------------------------------------------

    def set_data_type(self, data_type: DataTypes) -> None:
        if (
            data_type == DataTypes.FB_DATA_TYPE_UINT8
            or data_type == DataTypes.FB_DATA_TYPE_INT8
        ):
            self.__size = 1

        elif (
            data_type == DataTypes.FB_DATA_TYPE_UINT16
            or data_type == DataTypes.FB_DATA_TYPE_INT16
        ):
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
