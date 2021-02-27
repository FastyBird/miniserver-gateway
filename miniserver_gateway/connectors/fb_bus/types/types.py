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
from enum import Enum, unique


#
# Communication packets
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
@unique
class Packets(Enum):
    FB_PACKET_PAIR_DEVICE: int = 0x01

    FB_PACKET_READ_SINGLE_REGISTER: int = 0x03
    FB_PACKET_READ_MULTIPLE_REGISTERS: int = 0x05

    FB_PACKET_WRITE_SINGLE_REGISTER: int = 0x07
    FB_PACKET_WRITE_MULTIPLE_REGISTERS: int = 0x09

    FB_PACKET_REPORT_SINGLE_REGISTER: int = 0x0B

    FB_PACKET_READ_ONE_CONFIGURATION: int = 0x0D
    FB_PACKET_WRITE_ONE_CONFIGURATION: int = 0x0F
    FB_PACKET_REPORT_ONE_CONFIGURATION: int = 0x11

    FB_PACKET_PING: int = 0x13
    FB_PACKET_PONG: int = 0x15
    FB_PACKET_HELLO: int = 0x17

    FB_PACKET_GET_STATE: int = 0x19
    FB_PACKET_SET_STATE: int = 0x1B
    FB_PACKET_REPORT_STATE: int = 0x1D

    FB_PACKET_CONTROL_DEVICE: int = 0x1F

    FB_PACKET_PUBSUB_BROADCAST: int = 0x21
    FB_PACKET_PUBSUB_SUBSCRIBE: int = 0x23
    FB_PACKET_PUBSUB_UNSUBSCRIBE: int = 0x25

    FB_PACKET_EXCEPTION: int = 0x63

    @classmethod
    def has_value(cls, value: int) -> bool:
        return value in cls._value2member_map_


#
# Communication packets contents
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
@unique
class PacketsContents(Enum):
    FB_CONTENT_TERMINATOR: int = 0x00
    FB_CONTENT_DATA_SPACE: int = 0x20


#
# Communication protocol versions
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
@unique
class ProtocolVersions(Enum):
    PROTOCOL_V1: int = 0x01

    @classmethod
    def has_value(cls, value: int) -> bool:
        return value in cls._value2member_map_


#
# Pairing commands
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
@unique
class PairingCommands(Enum):
    FB_PAIRING_CMD_PROVIDE_ADDRESS: int = 0x01
    FB_PAIRING_CMD_SET_ADDRESS: int = 0x02
    FB_PAIRING_CMD_PROVIDE_ABOUT_INFO: int = 0x03
    FB_PAIRING_CMD_PROVIDE_DEVICE_MODEL: int = 0x04
    FB_PAIRING_CMD_PROVIDE_DEVICE_MANUFACTURER: int = 0x05
    FB_PAIRING_CMD_PROVIDE_DEVICE_VERSION: int = 0x06
    FB_PAIRING_CMD_PROVIDE_FIRMWARE_MANUFACTURER: int = 0x07
    FB_PAIRING_CMD_PROVIDE_FIRMWARE_VERSION: int = 0x08
    FB_PAIRING_CMD_PROVIDE_REGISTERS_SIZE: int = 0x09
    FB_PAIRING_CMD_PROVIDE_REGISTERS_STRUCTURE: int = 0x0A
    FB_PAIRING_CMD_PROVIDE_SETTINGS_SIZE: int = 0x0B
    FB_PAIRING_CMD_PROVIDE_SETTINGS_STRUCTURE: int = 0x0C
    FB_PAIRING_CMD_FINISHED: int = 0x0D

    @classmethod
    def has_value(cls, value: int) -> bool:
        return value in cls._value2member_map_


#
# Pairing responses
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
@unique
class PairingResponses(Enum):
    FB_PAIRING_RESPONSE_DEVICE_ADDRESS: int = 0x51
    FB_PAIRING_RESPONSE_ADDRESS_ACCEPTED: int = 0x52
    FB_PAIRING_RESPONSE_ABOUT_INFO: int = 0x53
    FB_PAIRING_RESPONSE_DEVICE_MODEL: int = 0x54
    FB_PAIRING_RESPONSE_DEVICE_MANUFACTURER: int = 0x55
    FB_PAIRING_RESPONSE_DEVICE_VERSION: int = 0x56
    FB_PAIRING_RESPONSE_FIRMWARE_MANUFACTURER: int = 0x57
    FB_PAIRING_RESPONSE_FIRMWARE_VERSION: int = 0x58
    FB_PAIRING_RESPONSE_REGISTERS_SIZE: int = 0x59
    FB_PAIRING_RESPONSE_REGISTERS_STRUCTURE: int = 0x5A
    FB_PAIRING_RESPONSE_SETTINGS_SIZE: int = 0x5B
    FB_PAIRING_RESPONSE_SETTINGS_STRUCTURE: int = 0x5C
    FB_PAIRING_RESPONSE_FINISHED: int = 0x5D

    @classmethod
    def has_value(cls, value: int) -> bool:
        return value in cls._value2member_map_


#
# Device states
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
@unique
class DeviceStates(Enum):
    FB_DEVICE_STATE_RUNNING: int = 0x01
    FB_DEVICE_STATE_STOPPED: int = 0x02
    FB_DEVICE_STATE_PAIRING: int = 0x03
    FB_DEVICE_STATE_ERROR: int = 0x04

    @classmethod
    def has_value(cls, value: int) -> bool:
        return value in cls._value2member_map_


#
# Device states
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
@unique
class DataTypes(Enum):
    FB_DATA_TYPE_UNKNOWN: int = 0xFF

    FB_DATA_TYPE_UINT8: int = 0x01
    FB_DATA_TYPE_UINT16: int = 0x02
    FB_DATA_TYPE_UINT32: int = 0x03
    FB_DATA_TYPE_INT8: int = 0x04
    FB_DATA_TYPE_INT16: int = 0x05
    FB_DATA_TYPE_INT32: int = 0x06
    FB_DATA_TYPE_FLOAT32: int = 0x07
    FB_DATA_TYPE_BOOL: int = 0x08
    FB_DATA_TYPE_TIME: int = 0x09
    FB_DATA_TYPE_DATE: int = 0x0A
    FB_DATA_TYPE_DATETIME: int = 0x0B

    @classmethod
    def has_value(cls, value: int) -> bool:
        return value in cls._value2member_map_


#
# Device registers types
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
@unique
class RegistersTypes(Enum):
    FB_REGISTER_DI: int = 0x01
    FB_REGISTER_DO: int = 0x02
    FB_REGISTER_AI: int = 0x03
    FB_REGISTER_AO: int = 0x04

    @classmethod
    def has_value(cls, value: int) -> bool:
        return value in cls._value2member_map_


#
# Device settings registers types
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
@unique
class SettingsTypes(Enum):
    FB_SETTINGS_DEVICE: int = 0x01
    FB_SETTINGS_REGISTER: int = 0x02

    @classmethod
    def has_value(cls, value: int) -> bool:
        return value in cls._value2member_map_
