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
from typing import Tuple

# App libs
from miniserver_gateway.connectors.fb_bus.types.types import (
    Packets,
    PairingCommands,
    RegistersTypes,
    SettingsTypes,
)
from miniserver_gateway.db.types import DeviceStates


#
# Device info entity
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class DeviceEntity:
    __id: uuid.UUID  # Device index in registry
    __address: int  # Device assigned address
    __state: DeviceStates = DeviceStates.STATE_UNKNOWN  # Device default state

    __serial_number: str or None = None
    __max_packet_length: int = pjon.PJON_PACKET_MAX_LENGTH
    __description_support: bool = False
    __settings_support: bool = False
    __pub_sub_support: bool = False

    __hw_model: str = "custom"
    __hw_manufacturer: str = "generic"
    __hw_version: str or None = None
    __fw_manufacturer: str = "generic"
    __fw_version: str or None = None

    __waiting_for_packet: Packets or None = None
    __last_packet_sent_timestamp: float = 0.0  # Timestamp when request was sent to the device

    __attempts: int = 0

    __sampling_time: float = 10.0

    __reading_registers_timestamp: float = 0.0
    __reading_register_address: int or None = None
    __reading_register_type: RegistersTypes or None = None

    __reading_settings_timestamp: float = 0.0
    __reading_setting_address: int or None = None
    __reading_setting_type: SettingsTypes or None = None

    __lost_timestamp: float = 0.0

    __pairing_cmd: PairingCommands or None = None

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        index: uuid.UUID,
        address: int,
        serial_number: str,
        max_packet_length: int,
        description_support: bool = False,
        settings_support: bool = False,
        pub_sub_support: bool = False,
    ) -> None:
        self.__id = index
        self.__address = address

        # Device basic configuration
        self.__serial_number = serial_number
        self.__max_packet_length = max_packet_length
        self.__description_support = description_support
        self.__settings_support = settings_support
        self.__pub_sub_support = pub_sub_support

    # -----------------------------------------------------------------------------

    def get_id(self) -> uuid.UUID:
        return self.__id

    # -----------------------------------------------------------------------------

    def get_state(self) -> DeviceStates:
        return self.__state

    # -----------------------------------------------------------------------------

    def set_state(self, state: DeviceStates) -> None:
        self.__state = state

        if state == DeviceStates.STATE_LOST:
            # Set lost timestamp
            self.__lost_timestamp = time.time()

            # Reset device communication state
            self.reset_communication()

            self.__last_packet_sent_timestamp = 0.0

        elif state == DeviceStates.STATE_READY:
            self.__reading_registers_timestamp = 0.0
            self.__reading_settings_timestamp = 0.0

    # -----------------------------------------------------------------------------

    def is_ready(self) -> bool:
        return self.__state == DeviceStates.STATE_RUNNING

    # -----------------------------------------------------------------------------

    def is_lost(self) -> bool:
        return self.__state == DeviceStates.STATE_LOST

    # -----------------------------------------------------------------------------

    def get_serial_number(self) -> str:
        return self.__serial_number

    # -----------------------------------------------------------------------------

    def get_address(self) -> int:
        return self.__address

    # -----------------------------------------------------------------------------

    def set_address(self, address: int) -> None:
        self.__address = address

    # -----------------------------------------------------------------------------

    def get_max_packet_length(self) -> int:
        return self.__max_packet_length

    # -----------------------------------------------------------------------------

    def set_max_packet_length(self, max_packet_length: int) -> None:
        self.__max_packet_length = max_packet_length

    # -----------------------------------------------------------------------------

    def has_description_support(self) -> bool:
        return self.__description_support

    # -----------------------------------------------------------------------------

    def set_description_support(self, description_support: bool) -> None:
        self.__description_support = description_support

    # -----------------------------------------------------------------------------

    def has_settings_support(self) -> bool:
        return self.__settings_support

    # -----------------------------------------------------------------------------

    def get_settings_support(self, settings_support: bool) -> None:
        self.__settings_support = settings_support

    # -----------------------------------------------------------------------------

    def has_pub_sub_support(self) -> bool:
        return self.__pub_sub_support

    # -----------------------------------------------------------------------------

    def set_pub_sub_support(self, pub_sub_support: bool) -> None:
        self.__pub_sub_support = pub_sub_support

    # -----------------------------------------------------------------------------

    def get_last_packet_timestamp(self) -> float:
        return self.__last_packet_sent_timestamp

    # -----------------------------------------------------------------------------

    def set_last_packet_timestamp(self, last_packet_sent: float) -> None:
        self.__last_packet_sent_timestamp = last_packet_sent

    # -----------------------------------------------------------------------------

    def get_waiting_for_packet(self) -> Packets or None:
        return self.__waiting_for_packet

    # -----------------------------------------------------------------------------

    def set_waiting_for_packet(self, waiting_for_packet: Packets) -> None:
        self.__waiting_for_packet = waiting_for_packet

    # -----------------------------------------------------------------------------

    def reset_waiting_for_packet(self) -> None:
        self.__waiting_for_packet = None

    # -----------------------------------------------------------------------------

    def get_attempts(self) -> int:
        return self.__attempts

    # -----------------------------------------------------------------------------

    def increment_attempts(self) -> None:
        self.__attempts = self.__attempts + 1

    # -----------------------------------------------------------------------------

    def set_pairing_cmd(self, cmd: PairingCommands or None) -> None:
        self.__pairing_cmd = cmd

    # -----------------------------------------------------------------------------

    def get_pairing_cmd(self) -> PairingCommands or None:
        return self.__pairing_cmd

    # -----------------------------------------------------------------------------

    def reset_communication(self) -> None:
        self.__waiting_for_packet = None
        self.__attempts = 0

    # -----------------------------------------------------------------------------

    def set_alive(self) -> None:
        self.set_state(DeviceStates(DeviceStates.STATE_UNKNOWN))

        # Reset device communication state
        self.reset_communication()
        self.__lost_timestamp = 0.0

    # -----------------------------------------------------------------------------

    def get_lost_timestamp(self) -> float:
        return self.__lost_timestamp

    # -----------------------------------------------------------------------------

    def get_last_register_reading_timestamp(self) -> float:
        return self.__reading_registers_timestamp

    # -----------------------------------------------------------------------------

    def get_sampling_time(self) -> float:
        return self.__sampling_time

    # -----------------------------------------------------------------------------

    def set_reading_register(self, register_address: int, register_type: RegistersTypes) -> None:
        self.__reading_register_address = register_address
        self.__reading_register_type = register_type

    # -----------------------------------------------------------------------------

    def get_reading_register(self) -> Tuple[int or None, RegistersTypes or None]:
        return self.__reading_register_address, self.__reading_register_type

    # -----------------------------------------------------------------------------

    def reset_reading_register(self, reset_timestamp: bool = False) -> None:
        if reset_timestamp:
            self.__reading_registers_timestamp = 0.0

        else:
            self.__reading_registers_timestamp = time.time()

        self.__reading_register_address = None
        self.__reading_register_type = None

    # -----------------------------------------------------------------------------

    def set_reading_setting(self, setting_address: int, setting_type: SettingsTypes) -> None:
        self.__reading_setting_address = setting_address
        self.__reading_setting_type = setting_type

    # -----------------------------------------------------------------------------

    def get_reading_setting(self) -> Tuple[int or None, SettingsTypes or None]:
        return self.__reading_setting_address, self.__reading_setting_type

    # -----------------------------------------------------------------------------

    def reset_reading_setting(self, reset_timestamp: bool = False) -> None:
        if reset_timestamp:
            self.__reading_settings_timestamp = 0.0

        else:
            self.__reading_settings_timestamp = time.time()

        self.__reading_setting_address = None
        self.__reading_setting_type = None

    # -----------------------------------------------------------------------------

    def get_hw_manufacturer(self) -> str:
        return self.__hw_manufacturer

    # -----------------------------------------------------------------------------

    def set_hw_manufacturer(self, manufacturer: str) -> None:
        self.__hw_manufacturer = manufacturer

    # -----------------------------------------------------------------------------

    def get_hw_model(self) -> str:
        return self.__hw_model

    # -----------------------------------------------------------------------------

    def set_hw_model(self, model: str) -> None:
        self.__hw_model = model

    # -----------------------------------------------------------------------------

    def get_hw_version(self) -> str or None:
        return self.__hw_version

    # -----------------------------------------------------------------------------

    def set_hw_version(self, version: str) -> None:
        self.__hw_version = version

    # -----------------------------------------------------------------------------

    def get_fw_manufacturer(self) -> str:
        return self.__fw_manufacturer

    # -----------------------------------------------------------------------------

    def set_fw_manufacturer(self, manufacturer: str) -> None:
        self.__fw_manufacturer = manufacturer

    # -----------------------------------------------------------------------------

    def get_fw_version(self) -> str or None:
        return self.__fw_version

    # -----------------------------------------------------------------------------

    def set_fw_version(self, version: str) -> None:
        self.__fw_version = version
