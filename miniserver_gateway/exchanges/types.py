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
from enum import Enum, unique


#
# Exchange routing keys
#
# @package        FastyBird:MiniServer!
# @subpackage     Exchange
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
@unique
class RoutingKeys(Enum):
    # Devices
    DEVICES_CREATED_ENTITY_ROUTING_KEY: str = "fb.bus.entity.created.device"
    DEVICES_UPDATED_ENTITY_ROUTING_KEY: str = "fb.bus.entity.updated.device"
    DEVICES_DELETED_ENTITY_ROUTING_KEY: str = "fb.bus.entity.deleted.device"

    DEVICES_CONTROLS_ROUTING_KEY: str = "fb.bus.control.device"

    # Devices properties
    DEVICES_PROPERTY_CREATED_ENTITY_ROUTING_KEY: str = (
        "fb.bus.entity.created.device.property"
    )
    DEVICES_PROPERTY_UPDATED_ENTITY_ROUTING_KEY: str = (
        "fb.bus.entity.updated.device.property"
    )
    DEVICES_PROPERTY_DELETED_ENTITY_ROUTING_KEY: str = (
        "fb.bus.entity.deleted.device.property"
    )

    DEVICES_PROPERTIES_DATA_ROUTING_KEY: str = "fb.bus.data.device.property"

    # Devices configuration
    DEVICES_CONFIGURATION_CREATED_ENTITY_ROUTING_KEY: str = (
        "fb.bus.entity.created.device.configuration"
    )
    DEVICES_CONFIGURATION_UPDATED_ENTITY_ROUTING_KEY: str = (
        "fb.bus.entity.updated.device.configuration"
    )
    DEVICES_CONFIGURATION_DELETED_ENTITY_ROUTING_KEY: str = (
        "fb.bus.entity.deleted.device.configuration"
    )

    DEVICES_CONFIGURATION_DATA_ROUTING_KEY: str = "fb.bus.data.device.configuration"

    # Channels
    CHANNELS_CREATED_ENTITY_ROUTING_KEY: str = "fb.bus.entity.created.channel"
    CHANNELS_UPDATED_ENTITY_ROUTING_KEY: str = "fb.bus.entity.updated.channel"
    CHANNELS_DELETED_ENTITY_ROUTING_KEY: str = "fb.bus.entity.deleted.channel"

    CHANNELS_CONTROLS_ROUTING_KEY: str = "fb.bus.control.channel"

    # Channels properties
    CHANNELS_PROPERTY_CREATED_ENTITY_ROUTING_KEY: str = (
        "fb.bus.entity.created.channel.property"
    )
    CHANNELS_PROPERTY_UPDATED_ENTITY_ROUTING_KEY: str = (
        "fb.bus.entity.updated.channel.property"
    )
    CHANNELS_PROPERTY_DELETED_ENTITY_ROUTING_KEY: str = (
        "fb.bus.entity.deleted.channel.property"
    )

    CHANNELS_PROPERTIES_DATA_ROUTING_KEY: str = "fb.bus.data.channel.property"

    # Channels configuration
    CHANNELS_CONFIGURATION_CREATED_ENTITY_ROUTING_KEY: str = (
        "fb.bus.entity.created.channel.configuration"
    )
    CHANNELS_CONFIGURATION_UPDATED_ENTITY_ROUTING_KEY: str = (
        "fb.bus.entity.updated.channel.configuration"
    )
    CHANNELS_CONFIGURATION_DELETED_ENTITY_ROUTING_KEY: str = (
        "fb.bus.entity.deleted.channel.configuration"
    )

    CHANNELS_CONFIGURATION_DATA_ROUTING_KEY: str = "fb.bus.data.channel.configuration"
