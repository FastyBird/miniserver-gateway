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
from miniserver_gateway.exceptions.invalid_argument import InvalidArgumentException


#
# Registers reading handler
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class ReadingHandler(Handler):
    __connector: FbBusConnectorInterface

    __READING_DELAY: float = 0.5  # Waiting delay before another packet is sent

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
        # About device info
        if packet == Packets.FB_PACKET_READ_MULTIPLE_REGISTERS:
            self.__read_multiple_registers_receiver(
                sender_address,
                payload,
                length
            )

        elif packet == Packets.FB_PACKET_READ_SINGLE_REGISTER:
            pass

    # -----------------------------------------------------------------------------

    def handle(
            self,
            device: DeviceEntity
    ) -> None:
        # Service is handling device in specific state
        if device.is_ready() is False:
            return

        # ...check for delay between broadcasting
        if (
                (
                        device.get_waiting_for_packet() is None
                        or
                        (
                                device.get_waiting_for_packet() is not None
                                and time.time() - device.get_last_packet_timestamp() >= self.__READING_DELAY
                        )
                ) and time.time() - device.get_last_register_reading_timestamp() >= device.get_sampling_time()
        ):
            self.__read_handler(device)

    # -----------------------------------------------------------------------------

    def __update_reading_pointer(
            self,
            device: DeviceEntity
    ) -> None:
        reading_address, reading_register_type = device.get_reading_register()

        if reading_register_type is not None:
            if reading_register_type == RegistersTypes.FB_REGISTER_DI:
                if len(self.__connector.get_registers_by_type(
                        device,
                        RegistersTypes(RegistersTypes.FB_REGISTER_DO)
                )) > 0:
                    device.set_reading_register(0, RegistersTypes(RegistersTypes.FB_REGISTER_DO))

                    return

                elif len(self.__connector.get_registers_by_type(
                        device,
                        RegistersTypes(RegistersTypes.FB_REGISTER_AI)
                )) > 0:
                    device.set_reading_register(0, RegistersTypes(RegistersTypes.FB_REGISTER_AI))

                    return

                elif len(self.__connector.get_registers_by_type(
                        device,
                        RegistersTypes(RegistersTypes.FB_REGISTER_AO)
                )) > 0:
                    device.set_reading_register(0, RegistersTypes(RegistersTypes.FB_REGISTER_AO))

                    return

            elif reading_register_type == RegistersTypes.FB_REGISTER_DO:
                if len(self.__connector.get_registers_by_type(
                        device,
                        RegistersTypes(RegistersTypes.FB_REGISTER_AI)
                )) > 0:
                    device.set_reading_register(0, RegistersTypes(RegistersTypes.FB_REGISTER_AI))

                    return

                elif len(self.__connector.get_registers_by_type(
                        device,
                        RegistersTypes(RegistersTypes.FB_REGISTER_AO)
                )) > 0:
                    device.set_reading_register(0, RegistersTypes(RegistersTypes.FB_REGISTER_AO))

                    return

            elif reading_register_type == RegistersTypes.FB_REGISTER_AI:
                if len(self.__connector.get_registers_by_type(
                        device,
                        RegistersTypes(RegistersTypes.FB_REGISTER_AO)
                )) > 0:
                    device.set_reading_register(0, RegistersTypes(RegistersTypes.FB_REGISTER_AO))

                    return

        device.reset_reading_register()

    # -----------------------------------------------------------------------------

    def __read_multiple_registers(
            self,
            device: DeviceEntity,
            register_type: RegistersTypes,
            start_address: int or None
    ) -> None:
        if register_type == RegistersTypes.FB_REGISTER_DI:
            register_size: int = len(self.__connector.get_registers_by_type(
                device,
                RegistersTypes(RegistersTypes.FB_REGISTER_DI)
            ))

        elif register_type == RegistersTypes.FB_REGISTER_DO:
            register_size: int = len(self.__connector.get_registers_by_type(
                device,
                RegistersTypes(RegistersTypes.FB_REGISTER_DO)
            ))

        elif register_type == RegistersTypes.FB_REGISTER_AI:
            register_size: int = len(self.__connector.get_registers_by_type(
                device,
                RegistersTypes(RegistersTypes.FB_REGISTER_AI)
            ))

        elif register_type == RegistersTypes.FB_REGISTER_AO:
            register_size: int = len(self.__connector.get_registers_by_type(
                device,
                RegistersTypes(RegistersTypes.FB_REGISTER_AO)
            ))

        else:
            raise InvalidArgumentException("Provided register type is not valid")

        if start_address is None:
            start_address: int = 0

        # 0 => Packet identifier
        # 1 => Register type
        # 2 => High byte of register address
        # 3 => Low byte of register address
        # 4 => High byte of registers length
        # 5 => Low byte of registers length
        # 6 => Packet null terminator
        output_content: list = [
            Packets(Packets.FB_PACKET_READ_MULTIPLE_REGISTERS).value,
            register_type.value,
            start_address >> 8,
            start_address & 0xFF,
        ]

        if (
                register_type == RegistersTypes.FB_REGISTER_DI
                or register_type == RegistersTypes.FB_REGISTER_DO
        ):
            # Calculate maximum count registers per one packet
            # eg. max_packet_length = 24 => max_readable_registers_count = 144
            #   - 144 digital registers could be read in one packet
            max_readable_registers_count: int = (device.get_max_packet_length() - 7) * 8

        elif (
                register_type == RegistersTypes.FB_REGISTER_AI
                or register_type == RegistersTypes.FB_REGISTER_AO
        ):
            # Calculate maximum count registers per one packet
            # eg. max_packet_length = 24 => max_readable_registers_count = 4
            #   - only 4 analog registers could be read in one packet
            max_readable_registers_count: int = (device.get_max_packet_length() - 7) // 4

        else:
            return

        # Calculate reading address based on maximum reading length and start address
        # eg. start_address = 0 and max_readable_registers_count = 3 => max_readable_addresses = 2
        # eg. start_address = 3 and max_readable_registers_count = 3 => max_readable_addresses = 5
        # eg. start_address = 0 and max_readable_registers_count = 8 => max_readable_addresses = 7
        max_readable_addresses: int = start_address + max_readable_registers_count - 1

        if (max_readable_addresses + 1) >= register_size:
            if start_address == 0:
                read_length: int = register_size
                next_address: int = start_address + read_length

            else:
                read_length: int = register_size - start_address
                next_address: int = start_address + read_length

        else:
            read_length: int = max_readable_registers_count
            next_address: int = start_address + read_length

        # Validate registers reading length
        if read_length <= 0:
            return

        output_content.append(read_length >> 8)
        output_content.append(read_length & 0xFF)

        output_content.append(PacketsContents(PacketsContents.FB_CONTENT_TERMINATOR).value)

        result: bool = self.__connector.send_packet(device.get_address(), output_content)

        if result is True:
            # Mark that gateway is waiting for reply from device...
            device.set_waiting_for_packet(Packets(Packets.FB_PACKET_READ_MULTIPLE_REGISTERS))
            # ...and store send timestamp
            device.set_last_packet_timestamp(time.time())
            # ...and increment communication counter
            device.increment_attempts()
            # ...and update reading pointer
            device.set_reading_register(next_address, register_type)

            # Check pointer against to registers size
            if (next_address + 1) > register_size:
                self.__update_reading_pointer(device)

        else:
            # Mark that gateway is not waiting any reply from device...
            device.reset_communication()

        self.__connector.update_device(device)

    # -----------------------------------------------------------------------------

    def __read_handler(
            self,
            device: DeviceEntity
    ) -> None:
        reading_address, reading_register_type = device.get_reading_register()

        if (
            len(self.__connector.get_registers_by_type(device, RegistersTypes(RegistersTypes.FB_REGISTER_DI))) > 0
            and (
                    reading_register_type == RegistersTypes.FB_REGISTER_DI
                    or reading_register_type is None
            )
        ):
            self.__read_multiple_registers(device, RegistersTypes(RegistersTypes.FB_REGISTER_DI), reading_address)

        elif (
            len(self.__connector.get_registers_by_type(device, RegistersTypes(RegistersTypes.FB_REGISTER_DO))) > 0
            and (
                    reading_register_type == RegistersTypes.FB_REGISTER_DO
                    or reading_register_type is None
            )
        ):
            self.__read_multiple_registers(device, RegistersTypes(RegistersTypes.FB_REGISTER_DO), reading_address)

        elif (
            len(self.__connector.get_registers_by_type(device, RegistersTypes(RegistersTypes.FB_REGISTER_AI))) > 0
            and (
                    reading_register_type == RegistersTypes.FB_REGISTER_AI
                    or reading_register_type is None
            )
        ):
            self.__read_multiple_registers(device, RegistersTypes(RegistersTypes.FB_REGISTER_AI), reading_address)

        elif (
            len(self.__connector.get_registers_by_type(device, RegistersTypes(RegistersTypes.FB_REGISTER_AO))) > 0
            and (
                    reading_register_type == RegistersTypes.FB_REGISTER_AO
                    or reading_register_type is None
            )
        ):
            self.__read_multiple_registers(device, RegistersTypes(RegistersTypes.FB_REGISTER_AO), reading_address)

    # -----------------------------------------------------------------------------

    # PAYLOAD:
    # 0     => Received packet identifier       => FB_PACKET_READ_MULTIPLE_REGISTERS
    # 1     => Registers type
    # 2     => High byte of register address
    # 3     => Low byte of register address
    # 4     => Count of data bytes
    # 5-n   => Packet data
    # n+1   => Packet null terminator           => FB_PACKET_TERMINATOR

    def __read_multiple_registers_receiver(
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

        # Extract registers types
        register_type: RegistersTypes = RegistersTypes(int(payload[1]))

        # Extract registers start address
        start_address: int = (int(payload[2]) << 8) | int(payload[3])

        # Extract registers count
        bytes_length: int = int(payload[4])

        if (
                register_type == RegistersTypes.FB_REGISTER_DI
                or register_type == RegistersTypes.FB_REGISTER_DO
        ):
            position_byte: int = 5

            register_address: int = start_address

            registers_count: int = len(self.__connector.get_registers_by_type(device, register_type))

            while position_byte < (payload_length - 1):
                # Fill the beginning with zeros to keep always full format
                data_byte: List[str] = list("{:0>8d}".format(int(str(bin(int(payload[position_byte])))[2:])))
                # Rotate bits to respect bit vs address
                data_byte.reverse()

                for i in range(8):
                    register: RegisterEntity = self.__connector.get_register_by_address(
                        device,
                        register_type,
                        register_address
                    )

                    if register is not None:
                        write_value: bool = True if int(data_byte[i]) & 0x01 else False

                        self.__connector.update_register_value(register, write_value)

                    register_address += 1

                    if register_address >= registers_count:
                        break

                position_byte += 1

        elif (
                register_type == RegistersTypes.FB_REGISTER_AI
                or register_type == RegistersTypes.FB_REGISTER_AO
        ):
            position_byte: int = 5

            register_address: int = start_address

            while (position_byte + 3) < (payload_length - 1):
                register: RegisterEntity = self.__connector.get_register_by_address(
                    device,
                    register_type,
                    register_address
                )

                if register is not None:
                    write_value: List[int] = [
                        int(payload[position_byte]),
                        int(payload[position_byte + 1]),
                        int(payload[position_byte + 2]),
                        int(payload[position_byte + 3]),
                    ]

                    transformed: int or float or None = RegistersHelper.transform_value_from_bytes(
                        register,
                        write_value
                    )

                    if transformed is not None:
                        self.__connector.update_register_value(register, transformed)

                position_byte += 4
                register_address += 1

        # Reset communication info
        device.reset_communication()

        self.__connector.update_device(device)
