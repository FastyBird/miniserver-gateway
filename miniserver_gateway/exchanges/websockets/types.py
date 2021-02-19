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
# Sockets OP codes
#
# @package        FastyBird:MiniServer!
# @subpackage     Exchange
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
@unique
class OPCodes(Enum):
    STREAM = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA


#
# WAMP messages codes
#
# @package        FastyBird:MiniServer!
# @subpackage     Exchange
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
@unique
class WampCodes(Enum):
    MSG_WELCOME: int = 0
    MSG_PREFIX: int = 1
    MSG_CALL: int = 2
    MSG_CALL_RESULT: int = 3
    MSG_CALL_ERROR: int = 4
    MSG_SUBSCRIBE: int = 5
    MSG_UNSUBSCRIBE: int = 6
    MSG_PUBLISH: int = 7
    MSG_EVENT: int = 8
