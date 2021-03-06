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
from typing import List

# App libs
from miniserver_gateway.connectors.connectors import log
from miniserver_gateway.connectors.fb_bus.fb_bus_connector_interface import FbBusConnectorInterface
from miniserver_gateway.connectors.fb_bus.entities.device import DeviceEntity
from miniserver_gateway.connectors.fb_bus.entities.register import RegisterEntity
from miniserver_gateway.connectors.fb_bus.handlers.handler import Handler
from miniserver_gateway.connectors.fb_bus.types.types import Packets, RegistersTypes
from miniserver_gateway.connectors.fb_bus.utilities.helpers import RegistersHelper


#
# Registers reading handler
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class ReportingHandler(Handler):
    __connector: FbBusConnectorInterface

    __READING_DELAY: float = 0.5  # Waiting delay before another packet is sent

    # -----------------------------------------------------------------------------

    def __init__(self, connector: FbBusConnectorInterface) -> None:
        self.__connector = connector

    # -----------------------------------------------------------------------------

    def receive(self, packet: Packets, sender_address: int, payload: str, length: int) -> None:
        # Get device info from registry
        device: DeviceEntity or None = self.__connector.get_device_by_address(sender_address)

        if device is None:
            return

        if packet == Packets.FB_PACKET_REPORT_SINGLE_REGISTER:
            self.__reported_single_registers_receiver(device, payload)

    # -----------------------------------------------------------------------------

    def handle(self, device: DeviceEntity) -> None:
        pass

    # -----------------------------------------------------------------------------

    # PAYLOAD:
    # 0     => Received packet identifier       => FB_PACKET_REPORT_SINGLE_REGISTER
    # 1     => Register type
    # 2     => High byte of register address
    # 3     => Low byte of register address
    # 4-n   => Packet data

    def __reported_single_registers_receiver(self, device: DeviceEntity, payload: str) -> None:
        if not RegistersTypes.has_value(int(payload[1])):
            log.warn("Received register type: {} is not valid".format(payload[1]))

            return

        # Extract register type
        register_type: RegistersTypes = RegistersTypes(int(payload[1]))

        # Extract register address
        register_address: int = (int(payload[2]) << 8) | int(payload[3])

        register: RegisterEntity = self.__connector.get_register_by_address(device, register_type, register_address)

        if register is not None:
            if register_type == RegistersTypes.FB_REGISTER_DI:
                write_value: int = (int(payload[4]) << 8) | int(payload[5])

                self.__connector.update_register_value(register, write_value == 0xFF00)

            elif register_type == RegistersTypes.FB_REGISTER_AI:
                write_value: List[int] = [
                    int(payload[4]),
                    int(payload[5]),
                    int(payload[6]),
                    int(payload[7]),
                ]

                transformed: int or float or None = RegistersHelper.transform_value_from_bytes(register, write_value)

                if transformed is not None:
                    self.__connector.update_register_value(register, transformed)
