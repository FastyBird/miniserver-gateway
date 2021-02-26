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
import pjon_cython as pjon
import time

# App libs
from miniserver_gateway.connectors.connectors import log
from miniserver_gateway.connectors.fb_bus.fb_bus_connector_interface import (
    FbBusConnectorInterface,
)
from miniserver_gateway.connectors.fb_bus.transport.transport import TransportInterface
from miniserver_gateway.connectors.fb_bus.types.types import Packets
from miniserver_gateway.connectors.fb_bus.utilities.packets_helper import PacketsHelper


#
# Storages container settings
#
# @package        FastyBird:MiniServer!
# @subpackage     Exchange
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class PjonTransportSettings:
    __address: int
    __serial_interface: str
    __baud_rate: int

    __MASTER_ADDRESS: int = 254
    __SERIAL_BAUD_RATE: int = 38400
    __SERIAL_INTERFACE: bytes = b"/dev/ttyAMA0"

    # -----------------------------------------------------------------------------

    def __init__(self, config: dict) -> None:
        self.__address = int(config.get("address", self.__MASTER_ADDRESS))
        self.__serial_interface = config.get(
            "serial_interface", self.__SERIAL_INTERFACE
        )
        self.__baud_rate = int(config.get("baud_rate", self.__SERIAL_BAUD_RATE))

    # -----------------------------------------------------------------------------

    @property
    def address(self) -> int:
        return self.__address

    # -----------------------------------------------------------------------------

    @property
    def serial_interface(self) -> str:
        return self.__serial_interface

    # -----------------------------------------------------------------------------

    @property
    def baud_rate(self) -> int:
        return self.__baud_rate


#
# FastyBird bus transport service
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class PjonTransport(TransportInterface, pjon.ThroughSerialAsync):
    __connector: FbBusConnectorInterface
    __settings: PjonTransportSettings

    # -----------------------------------------------------------------------------

    def __init__(self, config: dict, connector: FbBusConnectorInterface) -> None:
        self.__settings = PjonTransportSettings(config)

        pjon.ThroughSerialAsync.__init__(
            self,
            self.__settings.address,
            self.__settings.serial_interface,
            self.__settings.baud_rate,
        )

        self.__connector = connector

        self.set_synchronous_acknowledge(False)
        self.set_asynchronous_acknowledge(False)

    # -----------------------------------------------------------------------------

    def broadcast_packet(self, payload: list, waiting_time: float = 0.0) -> bool:
        return self.send_packet(pjon.PJON_BROADCAST, payload, waiting_time)

    # -----------------------------------------------------------------------------

    def send_packet(
        self, address: int, payload: list, waiting_time: float = 0.0
    ) -> bool:
        self.send(address, bytes(payload))

        # if result != pjon.PJON_ACK:
        #     if result == pjon.PJON_BUSY:
        #         log.warn(
        #             "Sending packet: {} for device: {} failed, bus is busy"
        #             .format(
        #                 PacketsHelpers.get_packet_name(int(payload[0])),
        #                 address
        #             )
        #         )
        #
        #     elif result == pjon.PJON_FAIL:
        #         log.warn(
        #             "Sending packet: {} for device: {} failed"
        #             .format(
        #                 PacketsHelpers.get_packet_name(int(payload[0])),
        #                 address
        #             )
        #         )
        #
        #     else:
        #         log.warn(
        #             "Sending packet: {} for device: {} failed, unknown error"
        #             .format(
        #                 PacketsHelpers.get_packet_name(int(payload[0])),
        #                 address
        #             )
        #         )
        #
        #     return False

        if address == pjon.PJON_BROADCAST:
            log.debug(
                "Successfully sent broadcast packet: {}".format(
                    PacketsHelper.get_packet_name(Packets(payload[0]))
                )
            )

        else:
            log.debug(
                "Successfully sent packet: {} for device with address: {}".format(
                    PacketsHelper.get_packet_name(Packets(payload[0])), address
                )
            )

        if waiting_time > 0:
            # Store start timestamp
            current_time: float = time.time()

            while (time.time() - current_time) <= waiting_time:
                packets_to_send, send_packet_result = self.loop()

                if send_packet_result == pjon.PJON_ACK:
                    return True

            return False

        return True

    # -----------------------------------------------------------------------------

    def run(self) -> int:
        try:
            result = self.loop()

            return int(result[0])

        except pjon.PJON_Connection_Lost:
            log.warn("Connection with device was lost")

        except pjon.PJON_Packets_Buffer_Full:
            log.warn("Buffer is full")

        except pjon.PJON_Content_Too_Long:
            log.warn("Content is long")

    # -----------------------------------------------------------------------------

    def receive(self, payload: str, length: int, packet_info) -> None:
        try:
            # Get sender address from header
            sender_address: int = int(packet_info["sender_id"])

        except KeyError:
            # Sender address is not present in header
            sender_address: None = None

        if Packets.has_value(int(payload[0])) is False:
            log.warn("Received unknown packet")

            return

        self.__connector.receive(sender_address, payload, length)
