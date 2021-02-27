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
from pony.orm import core as orm
from typing import Dict, Type

# App libs
from miniserver_gateway.db.models import (
    DeviceEntity,
    DevicePropertyEntity,
    DeviceConfigurationEntity,
    ChannelEntity,
    ChannelPropertyEntity,
    ChannelConfigurationEntity,
)
from miniserver_gateway.db.events import EntityChangedType
from miniserver_gateway.exchanges.types import RoutingKeys


#
# Data exchanges routing utils
#
# @package        FastyBird:MiniServer!
# @subpackage     Exchange
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class ExchangeRoutingUtils:

    CREATED_ENTITIES_ROUTING_KEYS_MAPPING: Dict[Type[orm.Entity], RoutingKeys] = {
        DeviceEntity: RoutingKeys.DEVICES_CREATED_ENTITY_ROUTING_KEY,
        DevicePropertyEntity: RoutingKeys.DEVICES_PROPERTY_CREATED_ENTITY_ROUTING_KEY,
        DeviceConfigurationEntity: RoutingKeys.DEVICES_CONFIGURATION_CREATED_ENTITY_ROUTING_KEY,
        ChannelEntity: RoutingKeys.CHANNELS_CREATED_ENTITY_ROUTING_KEY,
        ChannelPropertyEntity: RoutingKeys.CHANNELS_PROPERTY_CREATED_ENTITY_ROUTING_KEY,
        ChannelConfigurationEntity: RoutingKeys.CHANNELS_CONFIGURATION_CREATED_ENTITY_ROUTING_KEY,
    }

    UPDATED_ENTITIES_ROUTING_KEYS_MAPPING: Dict[Type[orm.Entity], RoutingKeys] = {
        DeviceEntity: RoutingKeys.DEVICES_UPDATED_ENTITY_ROUTING_KEY,
        DevicePropertyEntity: RoutingKeys.DEVICES_PROPERTY_UPDATED_ENTITY_ROUTING_KEY,
        DeviceConfigurationEntity: RoutingKeys.DEVICES_CONFIGURATION_UPDATED_ENTITY_ROUTING_KEY,
        ChannelEntity: RoutingKeys.CHANNELS_UPDATED_ENTITY_ROUTING_KEY,
        ChannelPropertyEntity: RoutingKeys.CHANNELS_PROPERTY_UPDATED_ENTITY_ROUTING_KEY,
        ChannelConfigurationEntity: RoutingKeys.CHANNELS_CONFIGURATION_UPDATED_ENTITY_ROUTING_KEY,
    }

    DELETED_ENTITIES_ROUTING_KEYS_MAPPING: Dict[Type[orm.Entity], RoutingKeys] = {
        DeviceEntity: RoutingKeys.DEVICES_DELETED_ENTITY_ROUTING_KEY,
        DevicePropertyEntity: RoutingKeys.DEVICES_PROPERTY_DELETED_ENTITY_ROUTING_KEY,
        DeviceConfigurationEntity: RoutingKeys.DEVICES_CONFIGURATION_DELETED_ENTITY_ROUTING_KEY,
        ChannelEntity: RoutingKeys.CHANNELS_DELETED_ENTITY_ROUTING_KEY,
        ChannelPropertyEntity: RoutingKeys.CHANNELS_PROPERTY_DELETED_ENTITY_ROUTING_KEY,
        ChannelConfigurationEntity: RoutingKeys.CHANNELS_CONFIGURATION_DELETED_ENTITY_ROUTING_KEY,
    }

    DATA_ROUTING_KEYS_MAPPING: Dict[Type[orm.Entity], RoutingKeys] = {
        DevicePropertyEntity: RoutingKeys.DEVICES_PROPERTIES_DATA_ROUTING_KEY,
        ChannelPropertyEntity: RoutingKeys.CHANNELS_PROPERTIES_DATA_ROUTING_KEY,
    }

    @staticmethod
    def get_entity_routing_key(entity: Type[orm.Entity], action_type: EntityChangedType) -> RoutingKeys or None:
        if action_type == EntityChangedType.ENTITY_CREATED:
            for classname in ExchangeRoutingUtils.CREATED_ENTITIES_ROUTING_KEYS_MAPPING:
                if issubclass(entity, classname):
                    return RoutingKeys(ExchangeRoutingUtils.CREATED_ENTITIES_ROUTING_KEYS_MAPPING[classname])

        elif action_type == EntityChangedType.ENTITY_UPDATED:
            for classname in ExchangeRoutingUtils.UPDATED_ENTITIES_ROUTING_KEYS_MAPPING:
                if issubclass(entity, classname):
                    return RoutingKeys(ExchangeRoutingUtils.UPDATED_ENTITIES_ROUTING_KEYS_MAPPING[classname])

        elif action_type == EntityChangedType.ENTITY_DELETED:
            for classname in ExchangeRoutingUtils.DELETED_ENTITIES_ROUTING_KEYS_MAPPING:
                if issubclass(entity, classname):
                    return RoutingKeys(ExchangeRoutingUtils.DELETED_ENTITIES_ROUTING_KEYS_MAPPING[classname])

        return None
