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
# Device states
#
# @package        FastyBird:MiniServer!
# @subpackage     Types
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
@unique
class DeviceStates(Enum):
    # Device is connected to gateway
    STATE_CONNECTED: str = "connected"
    # Device is disconnected from gateway
    STATE_DISCONNECTED: str = "disconnected"
    # Device is in initialization process
    STATE_INIT: str = "init"
    # Device is ready to operate
    STATE_READY: str = "ready"
    # Device is in operating mode
    STATE_RUNNING: str = "running"
    # Device is in sleep mode - support fow low power devices
    STATE_SLEEPING: str = "sleeping"
    # Device is not ready for receiving commands
    STATE_STOPPED: str = "stopped"
    # Connection with device is lost
    STATE_LOST: str = "lost"
    # Device has some error
    STATE_ALERT: str = "alert"
    # Device is in unknown state
    STATE_UNKNOWN: str = "unknown"


#
# Property data types
#
# @package        FastyBird:MiniServer!
# @subpackage     Types
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
@unique
class DataType(Enum):
    DATA_TYPE_CHAR: str = "char"
    DATA_TYPE_UCHAR: str = "uchar"
    DATA_TYPE_SHORT: str = "short"
    DATA_TYPE_USHORT: str = "ushort"
    DATA_TYPE_INT: str = "int"
    DATA_TYPE_UINT: str = "uint"
    DATA_TYPE_FLOAT: str = "float"
    DATA_TYPE_BOOLEAN: str = "bool"
    DATA_TYPE_STRING: str = "string"
    DATA_TYPE_ENUM: str = "enum"
    DATA_TYPE_COLOR: str = "color"


#
# Conditions operators
#
# @package        FastyBird:MiniServer!
# @subpackage     Types
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
@unique
class ConditionOperators(Enum):
    OPERATOR_VALUE_EQUAL: str = "eq"
    OPERATOR_VALUE_ABOVE: str = "above"
    OPERATOR_VALUE_BELOW: str = "below"
