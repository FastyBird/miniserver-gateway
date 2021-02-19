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
# App libs
from miniserver_gateway.connectors.connectors import log
from miniserver_gateway.connectors.fb_bus.fb_bus_connector_interface import FbBusConnectorInterface
from miniserver_gateway.connectors.fb_bus.entities.device import DeviceEntity
from miniserver_gateway.connectors.fb_bus.handlers.handler import Handler
from miniserver_gateway.connectors.fb_bus.utilities.helpers import Helpers
from miniserver_gateway.connectors.fb_bus.types.types import Packets, PacketsContents
from miniserver_gateway.db.types import DeviceStates


#
# Device state checking handler
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class CheckingHandler(Handler):
    __connector: FbBusConnectorInterface

    __MAX_TRANSMIT_ATTEMPTS: int = 5  # Maximum count of sending packets before gateway mark device as lost
    __PING_DELAY: float = 15.0  # Delay in s after reaching maximum packet sending attempts

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
        # Device responded to PING
        if packet == Packets.FB_PACKET_PONG:
            self.__pong_receiver(sender_address)

        # Device responded to set state request
        elif packet == Packets.FB_PACKET_GET_STATE:
            self.__get_state_receiver(sender_address, payload, length)

        # Device responded to set state request
        elif packet == Packets.FB_PACKET_SET_STATE:
            self.__set_state_receiver(sender_address, payload, length)

        # Device reported state
        elif packet == Packets.FB_PACKET_REPORT_STATE:
            self.__report_state_receiver(sender_address, payload, length)

    # -----------------------------------------------------------------------------

    def handle(
            self,
            device: DeviceEntity
    ) -> None:
        # Maximum send packet attempts was reached device is now marked as lost
        if device.get_attempts() >= self.__MAX_TRANSMIT_ATTEMPTS:
            was_lost: bool = device.get_lost_timestamp() > 0

            if was_lost is True:
                log.debug("Device with address: {} is still lost".format(device.get_address()))

            else:
                log.debug("Device with address: {} is lost".format(device.get_address()))

            device.set_state(DeviceStates(DeviceStates.STATE_LOST))

            self.__connector.update_device(device)

            self.__connector.propagate_device_state(device)

        # If device is marked as lost and wait for lost delay and then try to PING device
        if (
                device.is_lost()
                and (time.time() - device.get_lost_timestamp()) >= self.__PING_DELAY
                and (time.time() - device.get_last_packet_timestamp()) >= self.__PING_DELAY
        ):
            self.__send_ping_handler(device)

        # Device state is unknown, ask device for its state
        elif device.get_state() == DeviceStates.STATE_UNKNOWN:
            self.__send_get_device_state_handler(device)

    # -----------------------------------------------------------------------------

    def __send_ping_handler(
            self,
            device: DeviceEntity
    ) -> None:
        # 0 => Packet identifier
        # 1 => Packet null terminator
        output_content: list = [
            Packets(Packets.FB_PACKET_PING).value,
            PacketsContents(PacketsContents.FB_CONTENT_TERMINATOR).value
        ]

        result: bool = self.__connector.send_packet(
            device.get_address(),
            output_content
        )

        if result is True:
            # Mark that gateway is waiting for reply from device...
            device.set_waiting_for_packet(Packets(Packets.FB_PACKET_PONG))
            # ...and store send timestamp
            device.set_last_packet_timestamp(time.time())
            # ...and increment communication counter
            device.increment_attempts()

        else:
            # Mark that gateway is waiting for reply from device...
            device.reset_waiting_for_packet()
            # ...and store send timestamp
            device.set_last_packet_timestamp(time.time())
            # ...and increment communication counter
            device.increment_attempts()

        self.__connector.update_device(device)

    # -----------------------------------------------------------------------------

    def __send_get_device_state_handler(
            self,
            device: DeviceEntity
    ) -> None:
        # 0 => Packet identifier
        # 1 => Packet null terminator
        output_content: list = [
            Packets(Packets.FB_PACKET_GET_STATE).value,
            PacketsContents(PacketsContents.FB_CONTENT_TERMINATOR).value
        ]

        # Increment communication counter...
        device.increment_attempts()
        # ...and mark, that gateway is waiting for reply from device
        device.set_waiting_for_packet(Packets(Packets.FB_PACKET_GET_STATE))
        # ...and store broadcast timestamp
        device.set_last_packet_timestamp(time.time())

        self.__connector.update_device(device)

        result: bool = self.__connector.send_packet(
            device.get_address(),
            output_content,
            1
        )

        if result is False:
            # Mark that gateway is not waiting any reply from device...
            device.reset_communication()

            self.__connector.update_device(device)

    # -----------------------------------------------------------------------------

    # PAYLOAD:
    # 0 => Received packet identifier   => FB_PACKET_PONG
    # 1 => Packet null terminator       => FB_PACKET_TERMINATOR

    def __pong_receiver(
            self,
            sender_address: int
    ) -> None:
        # Get device info from registry
        device: DeviceEntity or None = self.__connector.get_device_by_address(sender_address)

        if device is None:
            return

        # Bring device back alive
        device.set_alive()

        self.__connector.update_device(device)

        self.__connector.propagate_device_state(device)

    # -----------------------------------------------------------------------------

    # PAYLOAD:
    # 0 => Received packet identifier   => FB_PACKET_GET_STATE
    # 1 => Device current state         => FB_PACKET_TERMINATOR
    # 2 => Packet null terminator       => FB_PACKET_TERMINATOR

    def __get_state_receiver(
            self,
            sender_address: int,
            payload: str,
            payload_length: int
    ) -> None:
        # Get device info from registry
        device: DeviceEntity or None = self.__connector.get_device_by_address(sender_address)

        if device is None:
            return

        # Validate packet structure
        if payload_length != 3:
            log.warn("Packet structure is invalid. Packet length is not as expected")

            return

        # Set received state
        device.set_state(Helpers.transform_state_for_gateway(int(payload[1])))

        self.__connector.update_device(device)

        self.__connector.propagate_device_state(device)

    # -----------------------------------------------------------------------------

    # PAYLOAD:
    # 0 => Received packet identifier   => FB_PACKET_SET_STATE
    # 1 => Device current state         => FB_PACKET_TERMINATOR
    # 2 => Packet null terminator       => FB_PACKET_TERMINATOR

    def __set_state_receiver(
            self,
            sender_address: int,
            payload: str,
            payload_length: int
    ) -> None:
        # Get device info from registry
        device: DeviceEntity or None = self.__connector.get_device_by_address(sender_address)

        if device is None:
            return

        # Validate packet structure
        if payload_length != 3:
            log.warn("Packet structure is invalid. Packet length is not as expected")

            return

    # -----------------------------------------------------------------------------

    # PAYLOAD:
    # 0 => Received packet identifier   => FB_PACKET_SET_STATE
    # 1 => Device current state         => FB_PACKET_TERMINATOR
    # 2 => Packet null terminator       => FB_PACKET_TERMINATOR

    def __report_state_receiver(
            self,
            sender_address: int,
            payload: str,
            payload_length: int
    ) -> None:
        # Get device info from registry
        device: DeviceEntity or None = self.__connector.get_device_by_address(sender_address)

        if device is None:
            return

        # Validate packet structure
        if payload_length != 3:
            log.warn("Packet structure is invalid. Packet length is not as expected")

            return

        # Set received state
        device.set_state(Helpers.transform_state_for_gateway(int(payload[1])))

        self.__connector.update_device(device)

        self.__connector.propagate_device_state(device)
