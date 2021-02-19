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
import time
from typing import List
# App libs
from miniserver_gateway.connectors.connectors import log
from miniserver_gateway.connectors.fb_bus.fb_bus_connector_interface import FbBusConnectorInterface
from miniserver_gateway.connectors.fb_bus.entities.device import DeviceEntity
from miniserver_gateway.connectors.fb_bus.entities.register import RegisterEntity
from miniserver_gateway.connectors.fb_bus.handlers.handler import Handler
from miniserver_gateway.connectors.fb_bus.types.types import Packets, PacketsContents, RegistersTypes
from miniserver_gateway.connectors.fb_bus.utilities.helpers import RegistersHelper


#
# Registers writing handler
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class WritingHandler(Handler):
    __connector: FbBusConnectorInterface

    __PACKET_RESPONSE_DELAY: float = 0.1

    # -----------------------------------------------------------------------------

    def __init__(
            self,
            connector: FbBusConnectorInterface
    ) -> None:
        self.__connector = connector

    # -----------------------------------------------------------------------------

    def receive(
            self,
            packet: Packets,
            sender_address: int,
            payload: str,
            length: int
    ) -> None:
        if packet == Packets.FB_PACKET_WRITE_SINGLE_REGISTER:
            self.__write_single_registers_receiver(
                sender_address,
                payload,
                length
            )

    # -----------------------------------------------------------------------------

    def handle(
            self,
            device: DeviceEntity
    ) -> None:
        pass

    # -----------------------------------------------------------------------------

    def write_value_to_register(
            self,
            register: RegisterEntity,
            write_value: bool or int
    ) -> None:
        device = self.__connector.get_device_by_id(register.get_device_id())

        # Service is handling device in specific state
        if device is None or device.is_ready() is False:
            return

        # 0     => Packet identifier
        # 1     => Register type
        # 2     => High byte of register address
        # 3     => Low byte of register address
        # 4-n   => Write value
        # n     => Packet null terminator
        output_content: list = [
            Packets(Packets.FB_PACKET_WRITE_SINGLE_REGISTER).value,
            register.get_type().value,
            register.get_address() >> 8,
            register.get_address() & 0xFF,
        ]

        if register.get_type() == RegistersTypes.FB_REGISTER_DO:
            if write_value:
                write_value: int = 0xFF00

            else:
                write_value: int = 0x0000

            output_content.append(write_value >> 8)
            output_content.append(write_value & 0xFF)

        elif register.get_type() == RegistersTypes.FB_REGISTER_AO:
            transformed: bytearray or None = RegistersHelper.transform_value_to_bytes(
                register,
                write_value
            )

            # Value could not be transformed
            if transformed is None:
                return

            output_content.append(transformed[0])
            output_content.append(transformed[1])
            output_content.append(transformed[2])
            output_content.append(transformed[3])

        else:
            return

        output_content.append(PacketsContents(PacketsContents.FB_CONTENT_TERMINATOR).value)  # Be sure to set the null terminator!!!

        # Increment communication counter...
        device.increment_attempts()
        # ...and mark, that gateway is waiting for reply from device
        device.set_waiting_for_packet(Packets(Packets.FB_PACKET_WRITE_SINGLE_REGISTER))
        # ...and store broadcast timestamp
        device.set_last_packet_timestamp(time.time())

        self.__connector.update_device(device)

        result: bool = self.__connector.send_packet(
            device.get_address(),
            output_content,
            self.__PACKET_RESPONSE_DELAY
        )

        if result is False:
            # Mark that gateway is not waiting any reply from device
            device.reset_communication()

            self.__connector.update_device(device)

    # -----------------------------------------------------------------------------

    # PAYLOAD:
    # 0     => Received packet identifier       => FB_PACKET_WRITE_SINGLE_REGISTER
    # 1     => Register type
    # 2     => High byte of register address
    # 3     => Low byte of register address
    # 4-n   => Packet data
    # n+1   => Packet null terminator           => FB_PACKET_TERMINATOR

    def __write_single_registers_receiver(
            self,
            sender_address: int,
            payload: str,
            payload_length: int
    ) -> None:
        # Get device info from registry
        device: DeviceEntity or None = self.__connector.get_device_by_address(sender_address)

        if device is None:
            return

        if not RegistersTypes.has_value(int(payload[1])):
            log.warn("Received register type: {} is not valid".format(payload[1]))

            return

        # Extract register type
        register_type: RegistersTypes = RegistersTypes(int(payload[1]))

        # Extract register address
        register_address: int = (int(payload[2]) << 8) | int(payload[3])

        register: RegisterEntity = self.__connector.get_register_by_address(
            device,
            register_type,
            register_address
        )

        if register is not None:
            if register_type == RegistersTypes.FB_REGISTER_DO:
                write_value: int = (int(payload[4]) << 8) | int(payload[5])

                self.__connector.update_register_value(register, write_value == 0xFF00)

            elif register_type == RegistersTypes.FB_REGISTER_AO:
                write_value: List[int] = [
                    int(payload[4]),
                    int(payload[5]),
                    int(payload[6]),
                    int(payload[7]),
                ]

                transformed: int or float or None = RegistersHelper.transform_value_from_bytes(register, write_value)

                if transformed is not None:
                    self.__connector.update_register_value(register, transformed)

        # Reset communication info
        device.reset_communication()

        self.__connector.update_device(device)
