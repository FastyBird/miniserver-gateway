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
import struct
from typing import List
# App libs
from miniserver_gateway.db.models import DevicePropertyEntity, DeviceConfigurationEntity,\
    ChannelPropertyEntity, ChannelConfigurationEntity
from miniserver_gateway.db.types import DeviceStates, DataType
from miniserver_gateway.exceptions.invalid_state import InvalidStateException
from miniserver_gateway.connectors.fb_bus.entities.register import RegisterEntity
from miniserver_gateway.connectors.fb_bus.entities.setting import DeviceSettingEntity, RegisterSettingEntity
from miniserver_gateway.connectors.fb_bus.types.types import Packets, PacketsContents,\
    DataTypes, DeviceStates as DevicePayloadStates


#
# BUS helpers
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class Helpers:

    @staticmethod
    def extract_text_from_payload(
            payload: str,
            start_pointer: int
    ) -> str:
        serial_number: List[chr] = []

        for i in range(start_pointer, len(payload)):
            if (
                    int(payload[i]) == PacketsContents(PacketsContents.FB_CONTENT_DATA_SPACE).value or
                    int(payload[i]) == PacketsContents(PacketsContents.FB_CONTENT_TERMINATOR).value
            ):
                break

            serial_number.append(chr(int(payload[i])))

        return "".join(serial_number)

    # -----------------------------------------------------------------------------

    @staticmethod
    def find_space_in_payload(
            payload: str,
            start_pointer: int
    ) -> int:
        for i in range(start_pointer, len(payload)):
            if int(payload[i]) == PacketsContents(PacketsContents.FB_CONTENT_DATA_SPACE).value:
                return i

        return -1

    # -----------------------------------------------------------------------------

    @staticmethod
    def transform_state_for_gateway(
            received_state: int
    ) -> DeviceStates:
        if DevicePayloadStates.has_value(received_state):
            device_state: DevicePayloadStates = DevicePayloadStates(received_state)

            if device_state == DevicePayloadStates.FB_DEVICE_STATE_RUNNING:
                # Device is running and ready for operate
                return DeviceStates(DeviceStates.STATE_RUNNING)

            elif device_state == DevicePayloadStates.FB_DEVICE_STATE_STOPPED:
                # Device is actually stopped
                return DeviceStates(DeviceStates.STATE_STOPPED)

            else:
                # Device is in unknown state
                return DeviceStates(DeviceStates.STATE_UNKNOWN)

        else:
            # Device is in unknown state
            return DeviceStates(DeviceStates.STATE_UNKNOWN)


#
# Property data type helpers
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class DataTypeHelper:

    @staticmethod
    def transform_for_gateway(
            item: RegisterEntity or DeviceSettingEntity or RegisterSettingEntity
    ) -> DataType or None:
        if item.get_data_type() == DataTypes.FB_DATA_TYPE_BOOL:
            return DataType(DataType.DATA_TYPE_BOOLEAN)

        elif item.get_data_type() == DataTypes.FB_DATA_TYPE_INT8:
            return DataType(DataType.DATA_TYPE_CHAR)

        elif item.get_data_type() == DataTypes.FB_DATA_TYPE_UINT8:
            return DataType(DataType.DATA_TYPE_UCHAR)

        elif item.get_data_type() == DataTypes.FB_DATA_TYPE_INT16:
            return DataType(DataType.DATA_TYPE_SHORT)

        elif item.get_data_type() == DataTypes.FB_DATA_TYPE_UINT16:
            return DataType(DataType.DATA_TYPE_USHORT)

        elif item.get_data_type() == DataTypes.FB_DATA_TYPE_INT32:
            return DataType(DataType.DATA_TYPE_INT)

        elif item.get_data_type() == DataTypes.FB_DATA_TYPE_UINT32:
            return DataType(DataType.DATA_TYPE_UINT)

        elif item.get_data_type() == DataTypes.FB_DATA_TYPE_FLOAT32:
            return DataType(DataType.DATA_TYPE_FLOAT)

        return None

    # -----------------------------------------------------------------------------

    @staticmethod
    def transform_for_device(
            entity: DevicePropertyEntity or ChannelPropertyEntity or DeviceConfigurationEntity or ChannelConfigurationEntity
    ) -> DataTypes:
        if entity.data_type == DataType.DATA_TYPE_BOOLEAN:
            return DataTypes(DataTypes.FB_DATA_TYPE_BOOL)

        elif entity.data_type == DataType.DATA_TYPE_CHAR:
            return DataTypes(DataTypes.FB_DATA_TYPE_INT8)

        elif entity.data_type == DataType.DATA_TYPE_UCHAR:
            return DataTypes(DataTypes.FB_DATA_TYPE_UINT8)

        elif entity.data_type == DataType.DATA_TYPE_SHORT:
            return DataTypes(DataTypes.FB_DATA_TYPE_INT16)

        elif entity.data_type == DataType.DATA_TYPE_USHORT:
            return DataTypes(DataTypes.FB_DATA_TYPE_UINT16)

        elif entity.data_type == DataType.DATA_TYPE_INT:
            return DataTypes(DataTypes.FB_DATA_TYPE_INT32)

        elif entity.data_type == DataType.DATA_TYPE_UINT:
            return DataTypes(DataTypes.FB_DATA_TYPE_UINT32)

        elif entity.data_type == DataType.DATA_TYPE_FLOAT:
            return DataTypes(DataTypes.FB_DATA_TYPE_FLOAT32)

        else:
            raise InvalidStateException(
                "Entity data type is not supported by this connector"
            )


#
# Registers helpers
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class RegistersHelper:

    @staticmethod
    def transform_value_from_bytes(
            register: RegisterEntity,
            write_value: List[int]
    ) -> int or float or None:
        if register.get_data_type() == DataTypes.FB_DATA_TYPE_FLOAT32:
            [transformed] = struct.unpack("<f", bytearray(write_value))

            return transformed

        elif (
                register.get_data_type() == DataTypes.FB_DATA_TYPE_UINT8
                or register.get_data_type() == DataTypes.FB_DATA_TYPE_UINT16
                or register.get_data_type() == DataTypes.FB_DATA_TYPE_UINT32
        ):
            [transformed] = struct.unpack("<I", bytearray(write_value))

            return transformed

        elif (
                register.get_data_type() == DataTypes.FB_DATA_TYPE_INT8
                or register.get_data_type() == DataTypes.FB_DATA_TYPE_INT16
                or register.get_data_type() == DataTypes.FB_DATA_TYPE_INT32
        ):
            [transformed] = struct.unpack("<i", bytearray(write_value))

            return transformed

        return None

    # -----------------------------------------------------------------------------

    @staticmethod
    def transform_value_to_bytes(
            register: RegisterEntity,
            write_value: int or float
    ) -> bytearray or None:
        if register.get_data_type() == DataTypes.FB_DATA_TYPE_FLOAT32:
            return struct.pack("<f", write_value)

        elif (
                register.get_data_type() == DataTypes.FB_DATA_TYPE_UINT8
                or register.get_data_type() == DataTypes.FB_DATA_TYPE_UINT16
                or register.get_data_type() == DataTypes.FB_DATA_TYPE_UINT32
        ):
            return struct.pack("<I", write_value)

        elif (
                register.get_data_type() == DataTypes.FB_DATA_TYPE_INT8
                or register.get_data_type() == DataTypes.FB_DATA_TYPE_INT16
                or register.get_data_type() == DataTypes.FB_DATA_TYPE_INT32
        ):
            return struct.pack("<i", write_value)

        return None
