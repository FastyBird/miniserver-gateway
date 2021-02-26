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
import uuid
from abc import ABC, abstractmethod
from typing import List

# App libs
from miniserver_gateway.connectors.fb_bus.entities.device import DeviceEntity
from miniserver_gateway.connectors.fb_bus.entities.register import RegisterEntity
from miniserver_gateway.connectors.fb_bus.entities.setting import (
    DeviceSettingEntity,
    RegisterSettingEntity,
)
from miniserver_gateway.connectors.fb_bus.types.types import (
    RegistersTypes,
    SettingsTypes,
)


#
# FastyBird bus connector interface
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class FbBusConnectorInterface(ABC):

    ADDRESS_NOT_ASSIGNED: int = 255

    @abstractmethod
    def receive(self, sender_address: int or None, payload: str, length: int) -> None:
        pass

    @abstractmethod
    def enable_searching(self) -> None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def disable_searching(self) -> None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def send_packet(
        self, address: int, payload: list, waiting_time: float = 0.0
    ) -> bool:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def broadcast_packet(self, payload: list, waiting_time: float = 0.0) -> bool:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def propagate_device(self, device: DeviceEntity) -> None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def propagate_register(self, register: RegisterEntity) -> None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def propagate_setting(
        self, register: DeviceSettingEntity or RegisterSettingEntity
    ) -> None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def propagate_device_state(self, updated_device: DeviceEntity) -> None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def get_device_by_id(self, identifier: uuid.UUID) -> DeviceEntity or None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def get_device_by_address(self, address: int) -> DeviceEntity or None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def get_device_by_serial_number(self, serial_number: str) -> DeviceEntity or None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def create_device(self, serial_number: str, max_packet_length: int) -> DeviceEntity:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def update_device(self, updated_device: DeviceEntity) -> None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def get_registers_by_type(
        self, device: DeviceEntity, register_type: RegistersTypes
    ) -> List[RegisterEntity]:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def get_register_by_address(
        self, device: DeviceEntity, register_type: RegistersTypes, register_address: int
    ) -> RegisterEntity or None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def create_register(
        self,
        device: DeviceEntity,
        register_address: int,
        register_type: RegistersTypes,
        register_data_type: int,
    ) -> RegisterEntity or None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def update_register(self, updated_register: RegisterEntity) -> None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def delete_register(self, deleted_register: RegisterEntity) -> None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def update_register_value(self, updated_register: RegisterEntity, value) -> None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def get_settings_by_type(
        self, device: DeviceEntity, settings_type: SettingsTypes
    ) -> List[DeviceSettingEntity or RegisterSettingEntity]:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def get_setting_by_address(
        self, device: DeviceEntity, setting_type: SettingsTypes, setting_address: int
    ) -> DeviceSettingEntity or RegisterSettingEntity or None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def create_setting(
        self, device: DeviceEntity, setting_address: int, setting_type: SettingsTypes
    ) -> RegisterEntity or None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def update_setting(
        self, updated_setting: DeviceSettingEntity or RegisterSettingEntity
    ) -> None:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def delete_setting(
        self, deleted_setting: DeviceSettingEntity or RegisterSettingEntity
    ) -> None:
        pass
