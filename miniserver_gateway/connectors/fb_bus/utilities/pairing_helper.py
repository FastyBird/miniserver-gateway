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
import uuid
import pjon_cython as pjon
from typing import List
# App libs
from miniserver_gateway.connectors.connectors import log
from miniserver_gateway.connectors.fb_bus.fb_bus_connector_interface import FbBusConnectorInterface
from miniserver_gateway.connectors.fb_bus.entities.device import DeviceEntity
from miniserver_gateway.connectors.fb_bus.entities.register import RegisterEntity
from miniserver_gateway.connectors.fb_bus.entities.setting import DeviceSettingEntity, RegisterSettingEntity
from miniserver_gateway.connectors.fb_bus.types.types import Packets, PacketsContents,\
    PairingCommands, PairingResponses,\
    DataTypes, RegistersTypes, SettingsTypes
from miniserver_gateway.connectors.fb_bus.utilities.helpers import Helpers
from miniserver_gateway.db.types import DeviceStates
from miniserver_gateway.exceptions.invalid_argument import InvalidArgumentException


#
# Device pairing handler
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class PairingHelper:
    __connector: FbBusConnectorInterface

    __pairing_device: uuid.UUID or None = None

    __last_pairing_request_broadcast: float = 0.0
    __attempts: int = 0

    __pairing_enabled: bool = False

    __MAX_SEARCHING_ATTEMPTS: int = 5
    __MAX_TRANSMIT_ATTEMPTS: int = 5  # Maximum count of sending packets before gateway mark device as lost
    __SEARCHING_DELAY: float = 6.0  # Waiting delay before another broadcast is sent
    __PACKET_RESPONSE_DELAY: float = 2.0

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
        # Unaddressed device responded to search request
        if packet == Packets.FB_PACKET_PAIR_DEVICE:
            # Get pairing cmd response
            pairing_response: PairingResponses = PairingResponses(int(payload[1]))

            if pairing_response == PairingResponses.FB_PAIRING_RESPONSE_DEVICE_ADDRESS:
                log.debug("Received pairing response: Device address")

                self.__device_address_receiver(
                    sender_address,
                    payload
                )

            elif pairing_response == PairingResponses.FB_PAIRING_RESPONSE_ADDRESS_ACCEPTED:
                log.debug("Received pairing response: Device confirmed address")

                self.__device_address_accepted_receiver(
                    sender_address,
                    payload
                )

            elif pairing_response == PairingResponses.FB_PAIRING_RESPONSE_ABOUT_INFO:
                log.debug("Received pairing response: Device provided about info")

                self.__device_about_info_receiver(
                    sender_address,
                    payload
                )

            elif (
                    pairing_response == PairingResponses.FB_PAIRING_RESPONSE_DEVICE_MODEL
                    or pairing_response == PairingResponses.FB_PAIRING_RESPONSE_DEVICE_MANUFACTURER
                    or pairing_response == PairingResponses.FB_PAIRING_RESPONSE_DEVICE_VERSION
                    or pairing_response == PairingResponses.FB_PAIRING_RESPONSE_FIRMWARE_MANUFACTURER
                    or pairing_response == PairingResponses.FB_PAIRING_RESPONSE_FIRMWARE_VERSION
            ):
                log.debug("Received pairing response: Device description")

                self.__device_description_receiver(
                    pairing_response,
                    sender_address,
                    payload
                )

            elif pairing_response == PairingResponses.FB_PAIRING_RESPONSE_REGISTERS_SIZE:
                log.debug("Received pairing response: Device registers sizes")

                self.__registers_size_receiver(
                    sender_address,
                    payload
                )

            elif pairing_response == PairingResponses.FB_PAIRING_RESPONSE_REGISTERS_STRUCTURE:
                log.debug("Received pairing response: Device registers structure")

                self.__registers_structure_receiver(
                    sender_address,
                    payload,
                    length
                )

            elif pairing_response == PairingResponses.FB_PAIRING_RESPONSE_SETTINGS_SIZE:
                log.debug("Received pairing response: Device settings sizes")

                self.__settings_size_receiver(
                    sender_address,
                    payload
                )

            elif pairing_response == PairingResponses.FB_PAIRING_RESPONSE_SETTINGS_STRUCTURE:
                log.debug("Received pairing response: Device settings structure")

                self.__settings_structure_receiver(
                    sender_address,
                    payload,
                    length
                )

            elif pairing_response == PairingResponses.FB_PAIRING_RESPONSE_FINISHED:
                log.debug("Received pairing response: Pairing finished")

                self.__pairing_finished_receiver(
                    sender_address,
                    payload
                )

    # -----------------------------------------------------------------------------

    def handle(
            self
    ) -> None:
        # Check if pairing mode is activated
        if self.__pairing_enabled is False:
            return

        # No device assigned for pairing
        if self.__pairing_device is None:
            # Check if search timeout is reached
            if self.__attempts >= self.__MAX_SEARCHING_ATTEMPTS:
                self.disable_pairing()

                # Reset counters
                self.__attempts = 0
                self.__last_pairing_request_broadcast = 0.0

            # Search timeout is not reached, new devices could be searched
            elif (
                    self.__last_pairing_request_broadcast == 0
                    or time.time() - self.__last_pairing_request_broadcast >= self.__SEARCHING_DELAY
            ):
                # Broadcast pairing request for new device
                self.__broadcast_pairing_request_handler()

                self.__attempts += 1
                self.__last_pairing_request_broadcast = time.time()

        # Device for pairing is assigned
        else:
            pairing_device: DeviceEntity = self.__connector.get_device_by_id(self.__pairing_device)

            if pairing_device is None:
                log.warn("Device for pairing could not be loaded from registry")

                self.__pairing_device = None
                self.disable_pairing()

                return

            # Max pairing attempts were reached
            if pairing_device.get_attempts() >= self.__MAX_TRANSMIT_ATTEMPTS:
                log.debug(
                    "Pairing for device with address: {} could not be finished. Device is lost"
                    .format(pairing_device.get_address())
                )

                # Pairing could not be finished
                pairing_device.set_state(DeviceStates(DeviceStates.STATE_LOST))

                self.__connector.update_device(pairing_device)

                self.__pairing_device = None
                self.disable_pairing()

                return

            if pairing_device.get_pairing_cmd() == PairingCommands.FB_PAIRING_CMD_SET_ADDRESS:
                if pairing_device.get_state() != DeviceStates.STATE_CONNECTED:
                    log.debug(
                        "Device is in invalid state, paring could not be finished"
                        .format(pairing_device.get_address())
                    )

                    self.__pairing_device = None
                    self.disable_pairing()

                    return

                self.__send_set_address_handler(pairing_device)

            else:
                if pairing_device.get_state() != DeviceStates.STATE_INIT:
                    log.debug(
                        "Device is in invalid state, paring could not be finished"
                        .format(pairing_device.get_address())
                    )

                    self.__pairing_device = None

                    return

                if (
                        pairing_device.get_pairing_cmd() == PairingCommands.FB_PAIRING_CMD_PROVIDE_ABOUT_INFO
                        or pairing_device.get_pairing_cmd() == PairingCommands.FB_PAIRING_CMD_PROVIDE_DEVICE_MODEL
                        or pairing_device.get_pairing_cmd() == PairingCommands.FB_PAIRING_CMD_PROVIDE_DEVICE_MANUFACTURER
                        or pairing_device.get_pairing_cmd() == PairingCommands.FB_PAIRING_CMD_PROVIDE_DEVICE_VERSION
                        or pairing_device.get_pairing_cmd() == PairingCommands.FB_PAIRING_CMD_PROVIDE_FIRMWARE_MANUFACTURER
                        or pairing_device.get_pairing_cmd() == PairingCommands.FB_PAIRING_CMD_PROVIDE_FIRMWARE_VERSION
                        or pairing_device.get_pairing_cmd() == PairingCommands.FB_PAIRING_CMD_PROVIDE_REGISTERS_SIZE
                        or pairing_device.get_pairing_cmd() == PairingCommands.FB_PAIRING_CMD_PROVIDE_SETTINGS_SIZE
                        or pairing_device.get_pairing_cmd() == PairingCommands.FB_PAIRING_CMD_FINISHED
                ):
                    self.__send_pairing_cmd_handler(
                        pairing_device,
                        pairing_device.get_pairing_cmd()
                    )

                elif pairing_device.get_pairing_cmd() == PairingCommands.FB_PAIRING_CMD_PROVIDE_REGISTERS_STRUCTURE:
                    self.__send_provide_registers_structure_handler(pairing_device)

                elif pairing_device.get_pairing_cmd() == PairingCommands.FB_PAIRING_CMD_PROVIDE_SETTINGS_STRUCTURE:
                    self.__send_provide_settings_structure_handler(pairing_device)

    # -----------------------------------------------------------------------------

    def enable_pairing(
            self
    ) -> None:
        self.__pairing_enabled = True

        log.debug("Pairing mode is activated")

    # -----------------------------------------------------------------------------

    def disable_pairing(
            self
    ) -> None:
        self.__pairing_enabled = False

        log.debug("Pairing mode is deactivated")

    # -----------------------------------------------------------------------------

    def is_pairing_enabled(
            self
    ) -> bool:
        return self.__pairing_enabled is True

    # -----------------------------------------------------------------------------

    def __configure_registers(
            self,
            device: DeviceEntity,
            registers_size: int,
            registers_type: RegistersTypes
    ) -> None:
        is_binary: bool = False

        if (
                registers_type == RegistersTypes.FB_REGISTER_DI
                or registers_type == RegistersTypes.FB_REGISTER_DO
        ):
            is_binary = True

        for i in range(registers_size):
            register: RegisterEntity or None = self.__connector.get_register_by_address(
                device,
                registers_type,
                i
            )

            if register is not None:
                if is_binary is True:
                    register.set_data_type(DataTypes(DataTypes.FB_DATA_TYPE_BOOL))

                else:
                    register.set_data_type(DataTypes(DataTypes.FB_DATA_TYPE_UNKNOWN))

                self.__connector.update_register(register)

            else:
                self.__connector.create_register(
                    device,
                    i,
                    registers_type,
                    DataTypes(DataTypes.FB_DATA_TYPE_BOOL if is_binary is True else DataTypes.FB_DATA_TYPE_UNKNOWN)
                )

        if registers_size < len(self.__connector.get_registers_by_type(device, registers_type)):
            for i in range(registers_size, len(self.__connector.get_registers_by_type(device, registers_type))):
                register: RegisterEntity or None = self.__connector.get_register_by_address(
                    device,
                    registers_type,
                    i
                )

                if register is not None:
                    self.__connector.delete_register(register)

    # -----------------------------------------------------------------------------

    def __configure_settings(
            self,
            device: DeviceEntity,
            settings_size: int,
            settings_type: SettingsTypes
    ) -> None:
        for i in range(settings_size):
            setting: DeviceSettingEntity or RegisterSettingEntity or None = self.__connector.get_setting_by_address(
                device,
                settings_type,
                i
            )

            if setting is None:
                self.__connector.create_setting(
                    device,
                    i,
                    settings_type
                )

        if settings_size < len(self.__connector.get_settings_by_type(device, settings_type)):
            for i in range(settings_size, len(self.__connector.get_settings_by_type(device, settings_type))):
                setting: DeviceSettingEntity or RegisterSettingEntity or None = self.__connector.get_setting_by_address(
                    device,
                    settings_type,
                    i
                )

                if setting is not None:
                    self.__connector.delete_setting(setting)

    # -----------------------------------------------------------------------------

    def __send_data_to_device(
            self,
            device: DeviceEntity,
            data: List[int]
    ) -> None:
        # Increment communication counter...
        device.increment_attempts()
        # ...and mark, that gateway is waiting for reply from device
        device.set_waiting_for_packet(Packets(Packets.FB_PACKET_PAIR_DEVICE))
        # ...and store broadcast timestamp
        device.set_last_packet_timestamp(time.time())

        self.__connector.update_device(device)

        result: bool = self.__connector.send_packet(
            device.get_address(),
            data,
            self.__PACKET_RESPONSE_DELAY
        )

        if result is False:
            # Mark that gateway is not waiting any reply from device
            device.reset_communication()

            self.__connector.update_device(device)

    # -----------------------------------------------------------------------------

    # Broadcast to all devices in pairing mode
    def __broadcast_pairing_request_handler(
            self
    ) -> None:
        # 0 => Packet identifier
        # 1 => Pairing command
        # 2 => Packet null terminator
        self.__connector.broadcast_packet([
            Packets(Packets.FB_PACKET_PAIR_DEVICE).value,
            PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_ADDRESS).value,
            PacketsContents(PacketsContents.FB_CONTENT_TERMINATOR).value,
        ], self.__PACKET_RESPONSE_DELAY)

    # -----------------------------------------------------------------------------

    def __send_set_address_handler(
            self,
            device: DeviceEntity
    ) -> None:
        # 0     => Packet identifier
        # 1     => Pairing command
        # 2     => Device assigned address
        # 3-n   => Device SN
        # n+1   => Packet null terminator
        output_content: List[int] = [
            Packets(Packets.FB_PACKET_PAIR_DEVICE).value,
            PairingCommands(PairingCommands.FB_PAIRING_CMD_SET_ADDRESS).value,
            device.get_address(),
        ]

        for i in range(len(device.get_serial_number())):
            output_content.append(ord(device.get_serial_number()[i]))

        output_content.append(PacketsContents(PacketsContents.FB_CONTENT_TERMINATOR).value)  # Be sure to set the null terminator!!!

        self.__send_data_to_device(device, output_content)

    # -----------------------------------------------------------------------------

    def __send_pairing_cmd_handler(
            self,
            device: DeviceEntity,
            command: PairingCommands
    ) -> None:
        # 0 => Packet identifier
        # 1 => Pairing command
        # 2 => Packet null terminator
        output_content: List[int] = [
            Packets(Packets.FB_PACKET_PAIR_DEVICE).value,
            command.value,
            PacketsContents(PacketsContents.FB_CONTENT_TERMINATOR).value
        ]

        self.__send_data_to_device(device, output_content)

    # -----------------------------------------------------------------------------

    def __send_provide_registers_structure_handler(
            self,
            device: DeviceEntity
    ) -> None:
        start_address, registers_type = device.get_reading_register()

        # 0 => Packet identifier
        # 1 => Pairing command
        # 2 => Registers type
        # 3 => High byte of registers address
        # 4 => Low byte of registers address
        # 5 => High byte of registers length
        # 6 => Low byte of registers length
        # 7 => Packet null terminator
        output_content: List[int] = [
            Packets(Packets.FB_PACKET_PAIR_DEVICE).value,
            PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_REGISTERS_STRUCTURE).value,
            registers_type.value,
            start_address >> 8,
            start_address & 0xFF
        ]

        if registers_type == RegistersTypes.FB_REGISTER_AI:
            registers_size: int = len(self.__connector.get_registers_by_type(
                device,
                RegistersTypes(RegistersTypes.FB_REGISTER_AI)
            ))

        elif registers_type == RegistersTypes.FB_REGISTER_AO:
            registers_size: int = len(self.__connector.get_registers_by_type(
                device,
                RegistersTypes(RegistersTypes.FB_REGISTER_AO)
            ))

        else:
            raise InvalidArgumentException("Provided register type: {} is not valid".format(registers_type))

        # Calculate maximum count registers per one packet
        # eg. max_packet_length = 8 => max_readable_registers_count = 3 - only 3 registers could be read in one packet
        max_readable_registers_count: int = device.get_max_packet_length() - 5

        # Calculate reading address based on maximum reading length and start address
        # eg. start_address = 0 and max_readable_registers_count = 3 => max_readable_addresses = 2
        # eg. start_address = 3 and max_readable_registers_count = 3 => max_readable_addresses = 5
        # eg. start_address = 0 and max_readable_registers_count = 8 => max_readable_addresses = 7
        max_readable_addresses: int = start_address + max_readable_registers_count - 1

        # register_size = 8 => address: 0__7
        # register_size = 16 => address: 0__15

        if (max_readable_addresses + 1) >= registers_size:
            if start_address == 0:
                output_content.append(registers_size >> 8)
                output_content.append(registers_size & 0xFF)

            else:
                output_content.append((registers_size - start_address) >> 8)
                output_content.append((registers_size - start_address) & 0xFF)

        else:
            output_content.append(max_readable_registers_count >> 8)
            output_content.append(max_readable_registers_count & 0xFF)

        output_content.append(PacketsContents(PacketsContents.FB_CONTENT_TERMINATOR).value)

        self.__send_data_to_device(device, output_content)

    # -----------------------------------------------------------------------------

    def __send_provide_settings_structure_handler(
            self,
            device: DeviceEntity
    ) -> None:
        start_address, setting_type = device.get_reading_setting()

        # 0 => Packet identifier
        # 1 => Pairing command
        # 2 => Registers type
        # 3 => High byte of settings address
        # 4 => Low byte of settings address
        # 5 => High byte of settings length
        # 6 => Low byte of settings length
        # 7 => Packet null terminator
        output_content: List[int] = [
            Packets(Packets.FB_PACKET_PAIR_DEVICE).value,
            PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_SETTINGS_STRUCTURE).value,
            setting_type.value,
            start_address >> 8,
            start_address & 0xFF
        ]

        if setting_type == SettingsTypes.FB_SETTINGS_DEVICE:
            settings_size: int = len(self.__connector.get_settings_by_type(
                device,
                SettingsTypes(SettingsTypes.FB_SETTINGS_DEVICE)
            ))

        elif setting_type == SettingsTypes.FB_SETTINGS_REGISTER:
            settings_size: int = len(self.__connector.get_settings_by_type(
                device,
                SettingsTypes(SettingsTypes.FB_SETTINGS_REGISTER)
            ))

        else:
            raise InvalidArgumentException("Provided setting type: {} is not valid".format(setting_type))

        # Calculate maximum count settings per one packet
        # eg. max_packet_length = 8 => max_readable_settings_count = 3 - only 3 settings could be read in one packet
        max_readable_settings_count: int = device.get_max_packet_length() - 5

        if setting_type == SettingsTypes.FB_SETTINGS_DEVICE:
            # Device settings structure is 12bytes long
            max_readable_settings_count = round(max_readable_settings_count / 12)

        else:
            # Register settings structure is 15bytes long
            max_readable_settings_count = round(max_readable_settings_count / 15)

        # Calculate reading address based on maximum reading length and start address
        # eg. start_address = 0 and max_readable_settings_count = 3 => max_readable_addresses = 2
        # eg. start_address = 3 and max_readable_settings_count = 3 => max_readable_addresses = 5
        # eg. start_address = 0 and max_readable_settings_count = 8 => max_readable_addresses = 7
        max_readable_addresses: int = start_address + max_readable_settings_count - 1

        # settings_size = 8 => address: 0__7
        # settings_size = 16 => address: 0__15

        if (max_readable_addresses + 1) >= settings_size:
            if start_address == 0:
                output_content.append(settings_size >> 8)
                output_content.append(settings_size & 0xFF)

            else:
                output_content.append((settings_size - start_address) >> 8)
                output_content.append((settings_size - start_address) & 0xFF)

        else:
            output_content.append(max_readable_settings_count >> 8)
            output_content.append(max_readable_settings_count & 0xFF)

        output_content.append(PacketsContents(PacketsContents.FB_CONTENT_TERMINATOR).value)

        self.__send_data_to_device(device, output_content)

    # -----------------------------------------------------------------------------

    # PAYLOAD:
    # 0    => Packet identifier         => FB_PACKET_PAIR_DEVICE
    # 1    => Cmd response              => FB_PAIRING_RESPONSE_DEVICE_ADDRESS
    # 2    => Device current address    => 1-253
    # 3-n  => Device parsed SN          => char array (a,b,c,...)
    # n+1  => Packet null terminator    => FB_PACKET_TERMINATOR

    def __device_address_receiver(
            self,
            sender_address: int,
            payload: str
    ) -> None:
        # Get sender supported max packet size
        device_current_address: int = int(payload[2])

        if device_current_address != sender_address:
            log.warn("Received packet with address mismatch: {} vs {}".format(sender_address, device_current_address))

            return

        # Extract sender serial number from payload
        serial_number: str = Helpers.extract_text_from_payload(payload, 3)

        # Try to find sender by serial number
        device: DeviceEntity or None = self.__connector.get_device_by_serial_number(serial_number)

        # Pairing new device...
        if device is None:
            # ..create new device in registry
            device: DeviceEntity = self.__connector.create_device(serial_number, pjon.PJON_PACKET_MAX_LENGTH)

            log.debug(
                "New device with SN: {} was successfully added to registry with address: {}"
                .format(
                    device.get_serial_number(),
                    device.get_address()
                )
            )

        elif (
                device_current_address != device.get_address()
                and device_current_address != self.__connector.ADDRESS_NOT_ASSIGNED
        ):
            # Device is registered but without known address
            if device.get_address() == self.__connector.ADDRESS_NOT_ASSIGNED:
                # Try to find device by current address...
                device_by_address: DeviceEntity or None = self.__connector.get_device_by_address(device_current_address)

                # ...and check if is same as device from whom packet was received
                if device_by_address is not None and device.get_serial_number() != device.get_serial_number():
                    log.warn("Received serial number: {} is not unique".format(serial_number))

                    return

                else:
                    device.set_address(device_current_address)

        if device_current_address == self.__connector.ADDRESS_NOT_ASSIGNED:
            # Device has not address
            device.set_state(DeviceStates(DeviceStates.STATE_CONNECTED))
            # Define next pairing command
            device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_SET_ADDRESS))

        else:
            # Device has address, continue in initialization
            device.set_state(DeviceStates(DeviceStates.STATE_INIT))
            # Define next pairing command
            device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_ABOUT_INFO))

        # Mark that gateway is not waiting any reply from device...
        device.reset_communication()

        self.__connector.update_device(device)

        self.__pairing_device = device.get_id()

        # Reset counters
        self.__attempts = 0
        self.__last_pairing_request_broadcast = 0.0

    # -----------------------------------------------------------------------------

    # PAYLOAD:
    # 0    => Packet identifier         => FB_PACKET_PAIR_DEVICE
    # 1    => Cmd response              => FB_PAIRING_RESPONSE_ADDRESS_ACCEPTED
    # 2-n  => Device parsed SN          => char array (a,b,c,...)
    # n+1  => Packet null terminator    => FB_PACKET_TERMINATOR

    def __device_address_accepted_receiver(
            self,
            sender_address: int,
            payload: str
    ) -> None:
        # Get device info from registry
        device: DeviceEntity or None = self.__connector.get_device_by_address(sender_address)

        if device is None:
            return

        # Extract sender serial number from payload
        serial_number: str = Helpers.extract_text_from_payload(payload, 2)

        if device.get_serial_number() != serial_number:
            log.warn("Device confirmed address assign, but with serial number mismatch")

            return

        # Device has address, continue in initialization
        device.set_state(DeviceStates(DeviceStates.STATE_INIT))
        # Define next pairing command
        device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_ABOUT_INFO))

        # Mark that gateway is not waiting any reply from device...
        device.reset_communication()

        self.__connector.update_device(device)

    # -----------------------------------------------------------------------------

    # PAYLOAD:
    # 0  => Packet identifier                        => FB_PACKET_PAIR_DEVICE
    # 1  => Cmd response                             => FB_PAIRING_RESPONSE_ABOUT_INFO
    # 2  => High byte of max packet length           => 0-255
    # 3  => Low byte of max packet length            => 0-255
    # 4  => High byte of device description support  => 0-255
    # 5  => Low byte of device description support   => 0-255
    # 6  => High byte of device settings support     => 0-255
    # 7  => Low byte of device settings support      => 0-255
    # 8  => High byte of device pub/sub support      => 0-255
    # 9  => Low byte of device pub/sub support       => 0-255
    # 10 => Packet null terminator                   => FB_PACKET_TERMINATOR

    def __device_about_info_receiver(
            self,
            sender_address: int,
            payload: str
    ) -> None:
        # Get device info from registry
        device: DeviceEntity or None = self.__connector.get_device_by_address(sender_address)

        if device is None:
            return

        max_packet_length: int = (int(payload[2]) << 8) | int(payload[3])
        description_support: bool = ((int(payload[4]) << 8) | int(payload[5])) == 0xFF00
        settings_support: bool = ((int(payload[6]) << 8) | int(payload[7])) == 0xFF00
        pub_sub_support: bool = ((int(payload[8]) << 8) | int(payload[9])) == 0xFF00

        # Device has provided maximum packet length
        device.set_max_packet_length(max_packet_length)
        # Device has provided description support status
        device.set_description_support(description_support)
        # Device has provided settings support status
        device.get_settings_support(settings_support)
        # Device has provided pub/sub support status
        device.set_pub_sub_support(pub_sub_support)

        if device.has_description_support():
            # Define next pairing command
            device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_DEVICE_MODEL))

        else:
            # Define next pairing command
            device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_REGISTERS_SIZE))

        # Mark that gateway is not waiting any reply from device...
        device.reset_communication()

        self.__connector.update_device(device)

    # -----------------------------------------------------------------------------

    # PAYLOAD:
    # 0     => Packet identifier            => FB_PACKET_PAIR_DEVICE
    # 1     => Cmd response
    # 2-n   => Description content          => char array(a, b, c, ...)
    # n+1   => Packet null terminator       => FB_PACKET_TERMINATOR

    def __device_description_receiver(
            self,
            response: PairingResponses,
            sender_address: int,
            payload: str
    ) -> None:
        # Get device info from registry
        device: DeviceEntity or None = self.__connector.get_device_by_address(sender_address)

        if device is None:
            return

        # Extract text content from payload
        content: str = Helpers.extract_text_from_payload(payload, 2)

        # HARDWARE

        if response == PairingResponses.FB_PAIRING_RESPONSE_DEVICE_MODEL:
            device.set_hw_model(content)

            # Define next pairing command
            device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_DEVICE_MANUFACTURER))

            log.debug(
                "Received device model: {} for device with address: {}"
                .format(content, device.get_address())
            )

        elif response == PairingResponses.FB_PAIRING_RESPONSE_DEVICE_MANUFACTURER:
            device.set_hw_manufacturer(content)

            # Define next pairing command
            device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_DEVICE_VERSION))

            log.debug(
                "Received device manufacturer: {} for device with address: {}"
                .format(content, device.get_address())
            )

        elif response == PairingResponses.FB_PAIRING_RESPONSE_DEVICE_VERSION:
            device.set_hw_version(content)

            # Define next pairing command
            device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_FIRMWARE_MANUFACTURER))

            log.debug(
                "Received device version: {} for device with address: {}"
                .format(content, device.get_address())
            )

        # FIRMWARE

        elif response == PairingResponses.FB_PAIRING_RESPONSE_FIRMWARE_MANUFACTURER:
            device.set_fw_manufacturer(content)

            # Define next pairing command
            device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_FIRMWARE_VERSION))

            log.debug(
                "Received device firmware manufacturer: {} for device with address: {}"
                .format(content, device.get_address())
            )

        elif response == PairingResponses.FB_PAIRING_RESPONSE_FIRMWARE_VERSION:
            device.set_fw_version(content)

            # Define next pairing command
            device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_REGISTERS_SIZE))

            log.debug(
                "Received device firmware version: {} for device with address: {}"
                .format(content, device.get_address())
            )

        # UNKNOWN

        else:
            log.debug("Received unknown description")
            return

        # Reset communication info
        device.reset_communication()

        self.__connector.update_device(device)

    # -----------------------------------------------------------------------------

    # PAYLOAD:
    # 0 => Packet identifier                => FB_PACKET_PAIR_DEVICE
    # 1 => Cmd response                     => FB_PAIRING_RESPONSE_REGISTERS_SIZE
    # 2 => DI buffer size                   => 0-255
    # 3 => DO buffer size                   => 0-255
    # 4 => AI buffer size                   => 0-255
    # 5 => AO buffer size                   => 0-255
    # 6 => Packet null terminator           => FB_PACKET_TERMINATOR

    def __registers_size_receiver(
            self,
            sender_address: int,
            payload: str
    ) -> None:
        # Get device info from registry
        device: DeviceEntity or None = self.__connector.get_device_by_address(sender_address)

        if device is None:
            return

        # DI registers
        self.__configure_registers(device, int(payload[2]), RegistersTypes(RegistersTypes.FB_REGISTER_DI))

        # DO registers
        self.__configure_registers(device, int(payload[3]), RegistersTypes(RegistersTypes.FB_REGISTER_DO))

        # AI registers
        self.__configure_registers(device, int(payload[4]), RegistersTypes(RegistersTypes.FB_REGISTER_AI))

        # AO registers
        self.__configure_registers(device, int(payload[5]), RegistersTypes(RegistersTypes.FB_REGISTER_AO))

        log.debug(
            "Configured registers: (DI: {}, DO: {}, AI: {}, AO: {}) for device with address: {}"
            .format(
                len(self.__connector.get_registers_by_type(device, RegistersTypes(RegistersTypes.FB_REGISTER_DI))),
                len(self.__connector.get_registers_by_type(device, RegistersTypes(RegistersTypes.FB_REGISTER_DO))),
                len(self.__connector.get_registers_by_type(device, RegistersTypes(RegistersTypes.FB_REGISTER_AI))),
                len(self.__connector.get_registers_by_type(device, RegistersTypes(RegistersTypes.FB_REGISTER_AO))),
                device.get_address(),
            )
        )

        if len(self.__connector.get_registers_by_type(device, RegistersTypes(RegistersTypes.FB_REGISTER_AI))) > 0:
            # Set registers reading address
            device.set_reading_register(0, RegistersTypes(RegistersTypes.FB_REGISTER_AI))

            # Define next pairing command
            device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_REGISTERS_STRUCTURE))

        elif len(self.__connector.get_registers_by_type(device, RegistersTypes(RegistersTypes.FB_REGISTER_AO))) > 0:
            # Set registers reading address
            device.set_reading_register(0, RegistersTypes(RegistersTypes.FB_REGISTER_AO))

            # Define next pairing command
            device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_REGISTERS_STRUCTURE))

        else:
            if device.has_settings_support():
                # Define next pairing command
                device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_SETTINGS_SIZE))

            else:
                # Define next pairing command
                device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_FINISHED))

        # Reset communication info
        device.reset_communication()

        self.__connector.update_device(device)

    # -----------------------------------------------------------------------------

    # PAYLOAD
    # 0     => Received packet identifier       => FB_PACKET_PAIR_DEVICE
    # 1     => Cmd response                     => FB_PAIRING_RESPONSE_REGISTERS_STRUCTURE
    # 2     => Register type
    # 3     => High byte of registers address   => 0-255
    # 4     => Low byte of registers address    => 0-255
    # 5     => High byte of registers length    => 0-255
    # 6     => Low byte of registers length     => 0-255
    # 7-n   => Register data type               => 0-255
    # n+1   => Packet null terminator           => FB_PACKET_TERMINATOR

    def __registers_structure_receiver(
            self,
            sender_address: int,
            payload: str,
            payload_length: int
    ) -> None:
        # Get device info from registry
        device: DeviceEntity or None = self.__connector.get_device_by_address(sender_address)

        if device is None:
            return

        if not RegistersTypes.has_value(int(payload[2])):
            return

        registers_type: RegistersTypes = RegistersTypes(int(payload[2]))

        start_address: int = (int(payload[3]) << 8) | int(payload[4])

        registers_length: int = (int(payload[5]) << 8) | int(payload[6])

        registers: List[RegisterEntity] = self.__connector.get_registers_by_type(device, registers_type)

        # Check if registers are created
        if len(registers) == 0:
            return

        byte_pointer: int = 7

        for i in range(start_address, payload_length):
            # Find register in model
            register: RegisterEntity or None = self.__connector.get_register_by_address(device, registers_type, i)

            if register is not None:
                if DataTypes.has_value(int(payload[byte_pointer])) is True:
                    # Configure register...
                    register.set_data_type(DataTypes(int(payload[byte_pointer])))

                    # Store updated register
                    self.__connector.update_register(register)

                else:
                    log.error("Received register data type is not valid")

            byte_pointer += 1

        # Reset communication info
        device.reset_communication()

        if len(registers) > (start_address + registers_length):
            # Set register reading address...
            device.set_reading_register((start_address + registers_length), registers_type)

        # Check if device has AO registers to initialize
        elif (
                registers_type == RegistersTypes.FB_REGISTER_AI
                and len(self.__connector.get_registers_by_type(
                    device,
                    RegistersTypes(RegistersTypes.FB_REGISTER_AO)
                )) > 0
        ):
            # Set registers reading address for next registers type
            device.set_reading_register(0, RegistersTypes(RegistersTypes.FB_REGISTER_AO))

        else:
            # Define next pairing command
            device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_SETTINGS_SIZE))

        self.__connector.update_device(device)

    # -----------------------------------------------------------------------------

    # PAYLOAD:
    # 0 => Packet identifier                => FB_PACKET_PAIR_DEVICE
    # 1 => Cmd response                     => FB_PAIRING_RESPONSE_SETTINGS_SIZE
    # 2 => Device settings buffer size      => 0-255
    # 3 => Registers settings buffer size   => 0-255
    # 4 => Packet null terminator           => FB_PACKET_TERMINATOR

    def __settings_size_receiver(
            self,
            sender_address: int,
            payload: str
    ) -> None:
        # Get device info from registry
        device: DeviceEntity or None = self.__connector.get_device_by_address(sender_address)

        if device is None:
            return

        # Device settings registers
        self.__configure_settings(device, int(payload[2]), SettingsTypes(SettingsTypes.FB_SETTINGS_DEVICE))

        # Registers settings registers
        self.__configure_settings(device, int(payload[3]), SettingsTypes(SettingsTypes.FB_SETTINGS_REGISTER))

        log.debug(
            "Configured settings: (Device: {}, Registers: {}) for device with address: {}"
            .format(
                len(self.__connector.get_settings_by_type(device, SettingsTypes(SettingsTypes.FB_SETTINGS_DEVICE))),
                len(self.__connector.get_settings_by_type(device, SettingsTypes(SettingsTypes.FB_SETTINGS_REGISTER))),
                device.get_address(),
            )
        )

        if len(self.__connector.get_settings_by_type(device, SettingsTypes(SettingsTypes.FB_SETTINGS_DEVICE))) > 0:
            # Set setting reading address
            device.set_reading_setting(0, SettingsTypes(SettingsTypes.FB_SETTINGS_DEVICE))

            # Define next pairing command
            device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_SETTINGS_STRUCTURE))

        elif len(self.__connector.get_settings_by_type(device, SettingsTypes(SettingsTypes.FB_SETTINGS_REGISTER))) > 0:
            # Set setting reading address
            device.set_reading_setting(0, SettingsTypes(SettingsTypes.FB_SETTINGS_REGISTER))

            # Define next pairing command
            device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_PROVIDE_SETTINGS_STRUCTURE))

        else:
            # Define next pairing command
            device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_FINISHED))

        # Reset communication info
        device.reset_communication()

        self.__connector.update_device(device)

    # -----------------------------------------------------------------------------

    # PAYLOAD
    # 0     => Received packet identifier       => FB_PACKET_PAIR_DEVICE
    # 1     => Cmd response                     => FB_PAIRING_RESPONSE_SETTINGS_STRUCTURE
    # 2     => Register type
    # 3     => High byte of settings address    => 0-255
    # 4     => Low byte of settings address     => 0-255
    # 5     => High byte of registers length    => 0-255
    # 6     => Low byte of registers length     => 0-255
    # 7-n   => Register data type               => 0-255
    # n+1   => Packet null terminator           => FB_PACKET_TERMINATOR

    def __settings_structure_receiver(
            self,
            sender_address: int,
            payload: str,
            payload_length: int
    ) -> None:
        # Get device info from registry
        device: DeviceEntity or None = self.__connector.get_device_by_address(sender_address)

        if device is None:
            return

        if not SettingsTypes.has_value(int(payload[2])):
            return

        settings_type: SettingsTypes = SettingsTypes(int(payload[2]))

        start_address: int = (int(payload[3]) << 8) | int(payload[4])

        read_length: int = (int(payload[5]) << 8) | int(payload[6])

        settings: List[DeviceSettingEntity or RegisterSettingEntity] = self.__connector.get_settings_by_type(
            device, settings_type
        )

        # Check if settings are created
        if len(settings) == 0:
            return

        byte_pointer: int = 7

        registers_counter: int = 0

        for i in range(start_address, payload_length):
            if settings_type == SettingsTypes.FB_SETTINGS_DEVICE:
                # Find setting in model
                setting: DeviceSettingEntity or None = self.__connector.get_setting_by_address(
                    device,
                    settings_type,
                    i
                )

                if setting is not None:
                    if DataTypes.has_value(int(payload[byte_pointer])):
                        data_type: DataTypes = DataTypes(int(payload[byte_pointer]))

                        name: str = Helpers.extract_text_from_payload(payload, byte_pointer + 1)

                        setting.set_data_type(data_type)
                        setting.set_name(name)

                        self.__connector.update_setting(setting)

                    else:
                        log.warn("Received device setting with unknown data type")

            else:
                # Find setting in model
                setting: RegisterSettingEntity or None = self.__connector.get_setting_by_address(
                    device,
                    settings_type,
                    i
                )

                if setting is not None:
                    if RegistersTypes.has_value(int(payload[byte_pointer + 2])):
                        register_address: int = (int(payload[byte_pointer]) << 8) | int(payload[byte_pointer + 1])

                        register_type: RegistersTypes = RegistersTypes(int(payload[byte_pointer + 2]))

                        register: RegisterEntity or None = self.__connector.get_register_by_address(
                            device,
                            register_type,
                            register_address
                        )

                        if register is not None:
                            if DataTypes.has_value(int(payload[byte_pointer + 3])):
                                data_type: DataTypes = DataTypes(int(payload[byte_pointer + 3]))

                                name: str = Helpers.extract_text_from_payload(payload, byte_pointer + 4)

                                setting.set_register(register.get_address(), register.get_type())
                                setting.set_data_type(data_type)
                                setting.set_name(name)

                                self.__connector.update_setting(setting)

                            else:
                                log.warn("Received register setting with unknown data type")

                        else:
                            log.warn("Received register setting for unknown register")

                    else:
                        log.warn("Received register setting for unknown register type")

            registers_counter += 1

            # Check if all settings were processed
            if registers_counter == read_length:
                break

            byte_pointer = Helpers.find_space_in_payload(payload, byte_pointer) + 1

        # Reset communication info
        device.reset_communication()

        if len(settings) > (start_address + registers_counter):
            # Set settings reading address...
            device.set_reading_setting((start_address + registers_counter), settings_type)

        # Check if device has registers settings to initialize
        elif (
                settings_type == SettingsTypes.FB_SETTINGS_DEVICE
                and len(self.__connector.get_settings_by_type(
                    device,
                    SettingsTypes(SettingsTypes.FB_SETTINGS_REGISTER)
                )) > 0
        ):
            # Set setting reading address for next setting type
            device.set_reading_setting(0, SettingsTypes(SettingsTypes.FB_SETTINGS_REGISTER))

        else:
            # Define next pairing command
            device.set_pairing_cmd(PairingCommands(PairingCommands.FB_PAIRING_CMD_FINISHED))

        self.__connector.update_device(device)

    # -----------------------------------------------------------------------------

    # PAYLOAD:
    # 0 => Packet identifier            => FB_PACKET_PAIR_DEVICE
    # 1 => Cmd response                 => FB_PAIRING_RESPONSE_FINISHED
    # 2 => Device actual state          => FB_DEVICE_STATE_RUNNING | FB_DEVICE_STATE_STOPPED | FB_DEVICE_STATE_ERROR
    # 3 => Packet null terminator       => FB_PACKET_TERMINATOR

    def __pairing_finished_receiver(
            self,
            sender_address: int,
            payload: str
    ) -> None:
        # Get device info from registry
        device: DeviceEntity or None = self.__connector.get_device_by_address(sender_address)

        if device is None:
            return

        # Disable pairing
        self.__pairing_device = None

        self.disable_pairing()

        # Set received state
        device.set_state(Helpers.transform_state_for_gateway(int(payload[2])))

        # Reset pairing command
        device.set_pairing_cmd(None)

        self.__connector.update_device(device)

        # Pairing finished, propagate device structure to gateway
        self.__connector.propagate_device(device)
