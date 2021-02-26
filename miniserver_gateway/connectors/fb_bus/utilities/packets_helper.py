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
from typing import Dict

# App libs
from miniserver_gateway.connectors.fb_bus.types.types import Packets


class PacketsHelper:

    PACKET_NAMES: Dict[Packets, str] = {
        Packets.FB_PACKET_PAIR_DEVICE: "FB_PACKET_PAIR_DEVICE",
        Packets.FB_PACKET_READ_SINGLE_REGISTER: "FB_PACKET_READ_SINGLE_REGISTER",
        Packets.FB_PACKET_READ_MULTIPLE_REGISTERS: "FB_PACKET_READ_MULTIPLE_REGISTERS",
        Packets.FB_PACKET_WRITE_SINGLE_REGISTER: "FB_PACKET_WRITE_SINGLE_REGISTER",
        Packets.FB_PACKET_WRITE_MULTIPLE_REGISTERS: "FB_PACKET_WRITE_MULTIPLE_REGISTERS",
        Packets.FB_PACKET_REPORT_SINGLE_REGISTER: "FB_PACKET_REPORT_SINGLE_REGISTER",
        Packets.FB_PACKET_READ_ONE_CONFIGURATION: "FB_PACKET_READ_ONE_CONFIGURATION",
        Packets.FB_PACKET_WRITE_ONE_CONFIGURATION: "FB_PACKET_WRITE_ONE_CONFIGURATION",
        Packets.FB_PACKET_REPORT_ONE_CONFIGURATION: "FB_PACKET_REPORT_ONE_CONFIGURATION",
        Packets.FB_PACKET_PING: "FB_PACKET_PING",
        Packets.FB_PACKET_PONG: "FB_PACKET_PONG",
        Packets.FB_PACKET_HELLO: "FB_PACKET_HELLO",
        Packets.FB_PACKET_GET_STATE: "FB_PACKET_GET_STATE",
        Packets.FB_PACKET_SET_STATE: "FB_PACKET_SET_STATE",
        Packets.FB_PACKET_REPORT_STATE: "FB_PACKET_REPORT_STATE",
        Packets.FB_PACKET_PUBSUB_BROADCAST: "FB_PACKET_PUBSUB_BROADCAST",
        Packets.FB_PACKET_PUBSUB_SUBSCRIBE: "FB_PACKET_PUBSUB_SUBSCRIBE",
        Packets.FB_PACKET_PUBSUB_UNSUBSCRIBE: "FB_PACKET_PUBSUB_UNSUBSCRIBE",
        Packets.FB_PACKET_EXCEPTION: "FB_PACKET_EXCEPTION",
    }

    @classmethod
    def get_packet_name(cls, packet: Packets) -> str:
        if packet in cls.PACKET_NAMES:
            return cls.PACKET_NAMES[packet]

        else:
            return "UNKNOWN"
