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
from threading import Thread
from typing import Dict, List, Set
from pony.orm import core as orm
import time

# App libs
from miniserver_gateway.db.models import ConnectorEntity, DeviceConnectorEntity
from miniserver_gateway.db.utils import EntityKeyHash
from miniserver_gateway.db.types import DeviceStates, DataType
from miniserver_gateway.exceptions.invalid_state import InvalidStateException
from miniserver_gateway.connectors.connectors import log, Connectors, ConnectorInterface
from miniserver_gateway.connectors.fb_bus.fb_bus_connector_interface import (
    FbBusConnectorInterface,
)
from miniserver_gateway.connectors.fb_bus.entities.device import DeviceEntity
from miniserver_gateway.connectors.fb_bus.entities.register import RegisterEntity
from miniserver_gateway.connectors.fb_bus.entities.setting import (
    DeviceSettingEntity,
    RegisterSettingEntity,
)
from miniserver_gateway.connectors.fb_bus.handlers.checking_handler import (
    CheckingHandler,
)
from miniserver_gateway.connectors.fb_bus.utilities.pairing_helper import PairingHelper
from miniserver_gateway.connectors.fb_bus.handlers.reading_handler import ReadingHandler
from miniserver_gateway.connectors.fb_bus.handlers.reporting_handler import (
    ReportingHandler,
)
from miniserver_gateway.connectors.fb_bus.handlers.writing_handler import WritingHandler
from miniserver_gateway.connectors.fb_bus.transport.pjon import PjonTransport
from miniserver_gateway.connectors.fb_bus.transport.transport import TransportInterface
from miniserver_gateway.connectors.fb_bus.types.types import (
    Packets,
    DataTypes,
    RegistersTypes,
    SettingsTypes,
)
from miniserver_gateway.connectors.fb_bus.utilities.helpers import DataTypeHelper
from miniserver_gateway.connectors.fb_bus.utilities.packets_helper import PacketsHelper


#
# FastyBird bus connector
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class FbBusConnector(ConnectorInterface, FbBusConnectorInterface, Thread):
    __stopped: bool = False

    __container: Connectors

    __transport: TransportInterface

    __connector: ConnectorEntity

    __packets_to_be_sent: int = 0
    __processed_devices: List[str] = []

    __search_for_devices: bool = True

    __pairing_helper: PairingHelper

    __checking_handler: CheckingHandler
    __reading_handler: ReadingHandler
    __reporting_handler: ReportingHandler
    __writing_handler: WritingHandler

    __devices: Dict[str, DeviceEntity] = set()
    __registers: Dict[str, RegisterEntity] = set()
    __devices_settings: Dict[str, DeviceSettingEntity] = set()
    __registers_settings: Dict[str, RegisterSettingEntity] = set()

    __MAX_ADDRESS: int = 253

    # -----------------------------------------------------------------------------

    def __init__(self, container: Connectors, connector: ConnectorEntity) -> None:
        Thread.__init__(self)

        self.__container = container
        self.__connector = connector

        # Data transport layer service
        self.__transport = PjonTransport(config=connector.params, connector=self)

        # Initialize connector handlers
        self.__checking_handler = CheckingHandler(self)
        self.__reading_handler = ReadingHandler(self)
        self.__reporting_handler = ReportingHandler(self)
        self.__writing_handler = WritingHandler(self)

        # Initialize connector helpers
        self.__pairing_helper = PairingHelper(self)

        # Threading config...
        self.setDaemon(True)
        self.setName("FB Bus connector thread")

    # -----------------------------------------------------------------------------

    def open(self) -> None:
        self.__stopped = False

        # Load & map all connector devices
        self.__load_devices()

        # Start connector thread
        self.start()

    # -----------------------------------------------------------------------------

    def close(self) -> None:
        self.__stopped = True

        # When connector is closing...
        for device_id in self.__devices:
            # ...set device state to disconnected
            self.__devices[device_id].set_state(DeviceStates(DeviceStates.STATE_DISCONNECTED))

        # And update device state in gateway
        for device_id in self.__devices:
            # Notify gateway about updates
            self.propagate_device_state(self.__devices[device_id])

    # -----------------------------------------------------------------------------

    def run(self) -> None:
        while True:
            # Check is pairing enabled
            if self.__pairing_helper.is_pairing_enabled() is True:
                self.__pairing_helper.handle()

            # Searching is not enabled...
            else:
                # Check packets queue
                if self.__packets_to_be_sent == 0:
                    # ...continue in communication

                    # Check for processing queue
                    if len(self.__processed_devices) == len(self.__devices):
                        self.__processed_devices = []

                    # Continue processing devices
                    for device_id in self.__devices:
                        if self.__devices[device_id].get_id().__str__() not in self.__processed_devices:
                            self.__checking_handler.handle(self.__devices[device_id])
                            self.__reading_handler.handle(self.__devices[device_id])

                            self.__processed_devices.append(device_id)

            self.__packets_to_be_sent = self.__transport.run()

            if self.__stopped:
                break

            time.sleep(0.001)

    # -----------------------------------------------------------------------------

    def publish(self, property_id: uuid.UUID, expected: bool or int or float or str or None) -> None:
        for register in self.__registers.values():
            if register.get_id() == property_id:
                if register.get_type() == RegistersTypes.FB_REGISTER_DO and expected == "toggle":
                    expected: bool = False if register.get_value() is True else True

                self.__writing_handler.write_value_to_register(register, expected)

    # -----------------------------------------------------------------------------

    def receive(self, sender_address: int or None, payload: str, length: int) -> None:
        # Get packet identifier from payload
        packet_id: Packets = Packets(int(payload[0]))

        if sender_address != self.ADDRESS_NOT_ASSIGNED and not self.__pairing_helper.is_pairing_enabled():
            device: DeviceEntity or None = self.get_device_by_address(sender_address)

            if device is None:
                log.warn("Received packet for unknown device")

                return

            # elif device.get_waiting_for_packet() is None or device.get_waiting_for_packet() != packet_id:
            #     log.warn(
            #         "Device with address: {} is not waiting for packet: {}"
            #         .format(
            #             device.get_address(),
            #             PacketsHelper.get_packet_name(packet_id)
            #         )
            #     )

            #    return

        log.debug(
            "Received packet: {} for device with address: {}".format(
                PacketsHelper.get_packet_name(packet_id), sender_address
            )
        )

        self.__pairing_helper.receive(packet_id, sender_address, payload, length)

        # In pairing mode only pairing packets are allowed to be processed
        if not self.__pairing_helper.is_pairing_enabled():
            self.__checking_handler.receive(packet_id, sender_address, payload, length)
            self.__reading_handler.receive(packet_id, sender_address, payload, length)
            self.__reporting_handler.receive(packet_id, sender_address, payload, length)
            self.__writing_handler.receive(packet_id, sender_address, payload, length)

    # -----------------------------------------------------------------------------

    def enable_searching(self) -> None:
        self.__pairing_helper.enable_pairing()

    # -----------------------------------------------------------------------------

    def disable_searching(self) -> None:
        self.__pairing_helper.disable_pairing()

    # -----------------------------------------------------------------------------

    def broadcast_packet(self, payload: list, waiting_time: float = 0.0) -> bool:
        return self.__transport.broadcast_packet(payload, waiting_time)

    # -----------------------------------------------------------------------------

    def send_packet(self, address: int, payload: list, waiting_time: float = 0.0) -> bool:
        return self.__transport.send_packet(address, payload, waiting_time)

    # -----------------------------------------------------------------------------

    def propagate_device(self, device: DeviceEntity) -> None:
        # Notify gateway about device structure
        self.__container.add_or_edit_device(
            connector_id=self.__connector.connector_id,
            device_id=device.get_id(),
            identifier=device.get_serial_number(),
            state=device.get_state(),
            connector_params={
                "address": device.get_address(),
                "max_packet_length": device.get_max_packet_length(),
                "description_support": device.has_description_support(),
                "settings_support": device.has_settings_support(),
                "pub_sub_support": device.has_pub_sub_support(),
            },
            hardware_manufacturer=device.get_hw_manufacturer(),
            hardware_model=device.get_hw_model(),
            hardware_version=device.get_hw_version(),
            firmware_manufacturer=device.get_fw_manufacturer(),
            firmware_version=device.get_fw_version(),
        )

        for register_type in RegistersTypes:
            registers: List[RegisterEntity] = self.get_registers_by_type(device, register_type)

            for register in registers:
                self.propagate_register(register)

        for setting_type in SettingsTypes:
            settings: List[DeviceSettingEntity or RegisterSettingEntity] = self.get_settings_by_type(
                device, setting_type
            )

            for setting in settings:
                self.propagate_setting(setting)

    # -----------------------------------------------------------------------------

    def propagate_register(self, register: RegisterEntity) -> None:
        if register.get_type() == RegistersTypes.FB_REGISTER_DI:
            channel_identifier: str = "di-{:0>2d}".format(register.get_address() + 1)

        elif register.get_type() == RegistersTypes.FB_REGISTER_DO:
            channel_identifier: str = "do-{:0>2d}".format(register.get_address() + 1)

        elif register.get_type() == RegistersTypes.FB_REGISTER_AI:
            channel_identifier: str = "ai-{:0>2d}".format(register.get_address() + 1)

        elif register.get_type() == RegistersTypes.FB_REGISTER_AO:
            channel_identifier: str = "ao-{:0>2d}".format(register.get_address() + 1)

        else:
            channel_identifier: str = "unknown-{:0>2d}".format(register.get_address() + 1)

        self.__container.add_or_edit_channel_property(
            device_id=register.get_device_id(),
            # Channel configuration
            channel_id=register.get_channel_id(),
            channel_identifier=channel_identifier,
            # Channel property configuration
            property_id=register.get_id(),
            property_identifier="register-{:0>2d}".format(register.get_address() + 1),
            key=register.get_key(),
            settable=register.is_writable(),
            queryable=True,
            data_type=DataTypeHelper.transform_for_gateway(register),
            unit=None,
            format=None,
        )

    # -----------------------------------------------------------------------------

    def propagate_setting(self, setting: DeviceSettingEntity or RegisterSettingEntity) -> None:
        if isinstance(setting, DeviceSettingEntity):
            self.__container.add_or_edit_device_configuration(
                device_id=setting.get_device_id(),
                # Setting configuration
                configuration_id=setting.get_id(),
                configuration_identifier="{}-{}".format(setting.get_name(), setting.get_address() + 1),
                data_type=DataTypeHelper.transform_for_gateway(setting),
            )

        else:
            device: DeviceEntity or None = self.get_device_by_id(setting.get_device_id())

            if device is None:
                return

            register: RegisterEntity or None = self.get_register_by_address(
                device, setting.get_register_type(), setting.get_register_address()
            )

            if register is None:
                return

            self.__container.add_or_edit_channel_configuration(
                device_id=setting.get_device_id(),
                # Channel configuration
                channel_id=register.get_channel_id(),
                # Setting configuration
                configuration_id=setting.get_id(),
                configuration_identifier="{}-{}".format(setting.get_name(), setting.get_address() + 1),
                data_type=DataTypeHelper.transform_for_gateway(setting),
            )

    # -----------------------------------------------------------------------------

    def propagate_device_state(self, device: DeviceEntity) -> None:
        # Notify gateway about state
        self.__container.add_or_edit_device(
            connector_id=self.__connector.connector_id,
            device_id=device.get_id(),
            identifier=device.get_serial_number(),
            state=device.get_state(),
        )

    # -----------------------------------------------------------------------------

    def get_device_by_id(self, identifier: uuid.UUID) -> DeviceEntity or None:
        if identifier.__str__() in self.__devices:
            return self.__devices[identifier.__str__()]

        return None

    # -----------------------------------------------------------------------------

    def get_device_by_address(self, address: int) -> DeviceEntity or None:
        for device_id in self.__devices:
            if self.__devices[device_id].get_address() == address:
                return self.__devices[device_id]

        return None

    # -----------------------------------------------------------------------------

    def get_device_by_serial_number(self, serial_number: str) -> DeviceEntity or None:
        for device_id in self.__devices:
            if self.__devices[device_id].get_serial_number() == serial_number:
                return self.__devices[device_id]

        return None

    # -----------------------------------------------------------------------------

    def create_device(self, serial_number: str, max_packet_length: int) -> DeviceEntity:
        reserved_addresses: List[int] = []

        for device_id in self.__devices:
            reserved_addresses.append(self.__devices[device_id].get_address())

        free_address: int or None = None

        for i in range(1, self.__MAX_ADDRESS):
            if i not in reserved_addresses:
                free_address = i

                break

        if free_address is None:
            raise InvalidStateException("New device with SN: {} could not be created".format(serial_number))

        device: DeviceEntity = DeviceEntity(uuid.uuid4(), free_address, serial_number, max_packet_length)

        device.set_state(DeviceStates(DeviceStates.STATE_CONNECTED))

        self.__devices[device.get_id().__str__()] = device

        return device

    # -----------------------------------------------------------------------------

    def update_device(self, updated_device: DeviceEntity) -> None:
        if updated_device.get_id().__str__() in self.__devices:
            self.__devices[updated_device.get_id().__str__()] = updated_device

    # -----------------------------------------------------------------------------

    def get_registers_by_type(self, device: DeviceEntity, register_type: RegistersTypes) -> List[RegisterEntity]:
        registers: List[RegisterEntity] = []

        for register in self.__registers.values():
            if register.get_device_id() == device.get_id() and register.get_type() == register_type:
                registers.append(register)

        return registers

    # -----------------------------------------------------------------------------

    def get_register_by_address(
        self, device: DeviceEntity, register_type: RegistersTypes, register_address: int
    ) -> RegisterEntity or None:
        for register in self.__registers.values():
            if (
                register.get_device_id() == device.get_id()
                and register.get_address() == register_address
                and register.get_type() == register_type
            ):
                return register

        return None

    # -----------------------------------------------------------------------------

    def create_register(
        self,
        device: DeviceEntity,
        register_address: int,
        register_type: RegistersTypes,
        register_data_type: DataTypes,
    ) -> RegisterEntity or None:
        register: RegisterEntity = RegisterEntity(
            uuid.uuid4(),
            EntityKeyHash.encode(int(time.time_ns() / 1000)),
            uuid.uuid4(),
            device.get_id(),
            register_address,
            register_type,
            register_data_type,
        )

        self.__registers[register.get_id().__str__()] = register

        return register

    # -----------------------------------------------------------------------------

    def update_register(self, updated_register: RegisterEntity) -> None:
        if updated_register.get_id().__str__() in self.__registers:
            self.__registers[updated_register.get_id().__str__()] = updated_register

    # -----------------------------------------------------------------------------

    def delete_register(self, deleted_register: RegisterEntity) -> None:
        if deleted_register.get_id().__str__() in self.__registers:
            del self.__registers[deleted_register.get_id().__str__()]

        # Notify gateway about deleting
        self.__container.delete_channel_property(deleted_register.get_id())

    # -----------------------------------------------------------------------------

    def update_register_value(self, register: RegisterEntity, value) -> None:
        previous_value = register.get_value()

        register.set_value(value)

        if register.get_id().__str__() in self.__registers:
            self.__registers[register.get_id().__str__()] = register

            self.__container.send_channel_property_to_storage(
                property_id=register.get_id(),
                actual_value=value,
                previous_value=previous_value,
            )

    # -----------------------------------------------------------------------------

    def get_settings_by_type(
        self, device: DeviceEntity, settings_type: SettingsTypes
    ) -> List[DeviceSettingEntity or RegisterSettingEntity]:
        settings: List[DeviceSettingEntity or RegisterSettingEntity] = []

        if settings_type == SettingsTypes.FB_SETTINGS_DEVICE:
            for setting in self.__devices_settings.values():
                if setting.get_device_id() == device.get_id():
                    settings.append(setting)

        elif settings_type == SettingsTypes.FB_SETTINGS_REGISTER:
            for setting in self.__registers_settings.values():
                if setting.get_device_id() == device.get_id():
                    settings.append(setting)

        return settings

    # -----------------------------------------------------------------------------

    def get_setting_by_address(
        self, device: DeviceEntity, setting_type: SettingsTypes, setting_address: int
    ) -> DeviceSettingEntity or RegisterSettingEntity or None:
        if setting_type == SettingsTypes.FB_SETTINGS_DEVICE:
            for register in self.__devices_settings.values():
                if register.get_device_id() == device.get_id() and register.get_address() == setting_address:
                    return register

        elif setting_type == SettingsTypes.FB_SETTINGS_REGISTER:
            for register in self.__registers_settings.values():
                if register.get_device_id() == device.get_id() and register.get_address() == setting_address:
                    return register

        return None

    # -----------------------------------------------------------------------------

    def create_setting(
        self, device: DeviceEntity, setting_address: int, setting_type: SettingsTypes
    ) -> DeviceSettingEntity or RegisterSettingEntity or None:
        if setting_type == SettingsTypes.FB_SETTINGS_DEVICE:
            setting: DeviceSettingEntity = DeviceSettingEntity(
                uuid.uuid4(),
                device.get_id(),
                setting_address,
            )

            self.__devices_settings[setting.get_id().__str__()] = setting

        else:
            setting: RegisterSettingEntity = RegisterSettingEntity(
                uuid.uuid4(),
                device.get_id(),
                setting_address,
            )

            self.__registers_settings[setting.get_id().__str__()] = setting

        return setting

    # -----------------------------------------------------------------------------

    def update_setting(self, updated_setting: DeviceSettingEntity or RegisterSettingEntity) -> None:
        if (
            isinstance(updated_setting, DeviceSettingEntity)
            and updated_setting.get_id().__str__() in self.__devices_settings
        ):
            self.__devices_settings[updated_setting.get_id().__str__()] = updated_setting

        elif (
            isinstance(updated_setting, RegisterSettingEntity)
            and updated_setting.get_id().__str__() in self.__registers_settings
        ):
            self.__registers_settings[updated_setting.get_id().__str__()] = updated_setting

    # -----------------------------------------------------------------------------

    def delete_setting(self, deleted_setting: DeviceSettingEntity or RegisterSettingEntity) -> None:
        if (
            isinstance(deleted_setting, DeviceSettingEntity)
            and deleted_setting.get_id().__str__() in self.__devices_settings
        ):
            del self.__devices_settings[deleted_setting.get_id().__str__()]

            # Notify gateway about deleting
            self.__container.delete_device_configuration(deleted_setting.get_id())

        elif (
            isinstance(deleted_setting, RegisterSettingEntity)
            and deleted_setting.get_id().__str__() in self.__registers_settings
        ):
            del self.__registers_settings[deleted_setting.get_id().__str__()]

            # Notify gateway about deleting
            self.__container.delete_channel_configuration(deleted_setting.get_id())

    # -----------------------------------------------------------------------------

    @orm.db_session
    def __load_devices(self) -> None:
        self.__devices = dict()
        self.__registers = dict()
        self.__devices_settings = dict()
        self.__registers_settings = dict()

        invalid_address: int = self.ADDRESS_NOT_ASSIGNED

        # Process all connector devices...
        for connector_device in DeviceConnectorEntity.select(
            lambda cd: cd.connector.connector_id == self.__connector.connector_id
        ):
            try:
                device_connector_params: dict = connector_device.params if connector_device.params is not None else {}

                device: DeviceEntity = DeviceEntity(
                    connector_device.device.device_id,
                    int(device_connector_params.get("address", invalid_address)),
                    connector_device.device.identifier,
                    device_connector_params.get("max_packet_length", 1536),
                    device_connector_params.get("description_support", False),
                    device_connector_params.get("settings_support", False),
                    device_connector_params.get("pub_sub_support", False),
                )

                # For now, device state is unknown
                device.set_state(DeviceStates(DeviceStates.STATE_UNKNOWN))

                device_registers: Set[RegisterEntity] = set()
                device_settings: Set[DeviceSettingEntity] = set()
                registers_settings: Set[RegisterSettingEntity] = set()

                # ... and process all device channels...
                for channel in connector_device.device.channels:
                    # ...and map channel properties to registers
                    for channel_property in channel.properties:
                        try:
                            # Transform property name to prefix & address
                            (
                                register_prefix,
                                register_address,
                            ) = channel_property.identifier.split("-")

                        except ValueError:
                            log.warn("Channel property name is not in expected format")

                            continue

                        if (
                            isinstance(register_address, str) is False
                            or register_address.isnumeric() is False
                            or int(register_address) <= 0
                        ):
                            log.warn("Channel property name is not in expected format")

                            continue

                        if channel_property.data_type == DataType.DATA_TYPE_BOOLEAN:
                            if channel_property.settable is True:
                                register_type: RegistersTypes = RegistersTypes(RegistersTypes.FB_REGISTER_DO)

                            else:
                                register_type: RegistersTypes = RegistersTypes(RegistersTypes.FB_REGISTER_DI)

                        else:
                            if channel_property.settable is True:
                                register_type: RegistersTypes = RegistersTypes(RegistersTypes.FB_REGISTER_AO)

                            else:
                                register_type: RegistersTypes = RegistersTypes(RegistersTypes.FB_REGISTER_AI)

                        device_registers.add(
                            RegisterEntity(
                                channel_property.property_id,
                                channel_property.key,
                                channel.channel_id,
                                connector_device.device.device_id,
                                (int(register_address) - 1),
                                register_type,
                                DataTypeHelper.transform_for_device(channel_property),
                            )
                        )

                    # ...and map channel configuration to registers
                    for channel_configuration in channel.configuration:
                        try:
                            # Transform property name to prefix & address
                            (
                                setting_prefix,
                                setting_address,
                            ) = channel_configuration.identifier.split("-")

                        except ValueError:
                            log.warn("Channel setting name is not in expected format")

                            continue

                        if (
                            isinstance(setting_address, str) is False
                            or setting_address.isnumeric() is False
                            or int(setting_address) <= 0
                        ):
                            log.warn("Channel setting name is not in expected format")

                            continue

                        setting: RegisterSettingEntity = RegisterSettingEntity(
                            channel_configuration.configuration_id,
                            connector_device.device.device_id,
                            (int(setting_address) - 1),
                        )

                        setting.set_name(setting_prefix)
                        setting.set_data_type(DataTypeHelper.transform_for_device(channel_configuration))
                        setting.set_value(channel_configuration.value)

                        registers_settings.add(setting)

                self.__devices[device.get_id().__str__()] = device

                for device_register in device_registers:
                    self.__registers[device_register.get_id().__str__()] = device_register

                for device_setting in device_settings:
                    self.__devices_settings[device_setting.get_id().__str__()] = device_setting

                for register_setting in registers_settings:
                    self.__registers_settings[register_setting.get_id().__str__()] = register_setting

            except Exception as e:
                log.error("Error on loading connector device:")
                log.exception(e)
