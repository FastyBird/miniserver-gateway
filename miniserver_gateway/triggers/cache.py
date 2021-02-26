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
from abc import ABC
from pony.orm import core as orm
from typing import Dict, List

# App libs
from miniserver_gateway.db.cache import DevicePropertyItem, ChannelPropertyItem
from miniserver_gateway.db.models import (
    TriggerEntity,
    AutomaticTriggerEntity,
    DevicePropertyConditionEntity,
    ChannelPropertyConditionEntity,
    ChannelPropertyActionEntity,
)
from miniserver_gateway.db.types import ConditionOperators
from miniserver_gateway.utils.properties import PropertiesUtils


#
# Trigger item
#
# @package        FastyBird:MiniServer!
# @subpackage     Trigger
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class TriggerItem:
    __trigger_id: uuid.UUID

    __device_property_conditions: Dict[str, "DevicePropertyConditionItem"] = dict()
    __channel_property_conditions: Dict[str, "ChannelPropertyConditionItem"] = dict()

    __device_property_actions: Dict[str, "DevicePropertyActionItem"] = dict()
    __channel_property_actions: Dict[str, "ChannelPropertyActionItem"] = dict()

    __is_fulfilled = False
    __is_triggered = False

    # -----------------------------------------------------------------------------

    def __init__(self, trigger_id: uuid.UUID) -> None:
        self.__trigger_id = trigger_id

        self.__device_property_actions = dict()
        self.__channel_property_actions = dict()

        self.__device_property_conditions = dict()
        self.__channel_property_conditions = dict()

        self.__is_fulfilled = False
        self.__is_triggered = False

    # -----------------------------------------------------------------------------

    @property
    def trigger_id(self) -> uuid.UUID:
        return self.__trigger_id

    # -----------------------------------------------------------------------------

    @property
    def is_fulfilled(self) -> bool:
        return self.__is_fulfilled

    # -----------------------------------------------------------------------------

    @property
    def is_triggered(self) -> bool:
        return self.__is_triggered

    # -----------------------------------------------------------------------------

    @property
    def actions(
        self,
    ) -> Dict[str, "DevicePropertyConditionItem" or "ChannelPropertyConditionItem"]:
        return {**self.__device_property_actions, **self.__channel_property_actions}

    # -----------------------------------------------------------------------------

    @property
    def conditions(
        self,
    ) -> Dict[str, "DevicePropertyConditionItem" or "ChannelPropertyConditionItem"]:
        return {
            **self.__device_property_conditions,
            **self.__channel_property_conditions,
        }

    # -----------------------------------------------------------------------------

    def add_condition(
        self,
        condition_id: str,
        condition: "DevicePropertyConditionItem" or "ChannelPropertyConditionItem",
    ) -> None:
        if isinstance(condition, DevicePropertyConditionItem):
            self.__device_property_conditions[condition_id] = condition

        elif isinstance(condition, ChannelPropertyConditionItem):
            self.__channel_property_conditions[condition_id] = condition

    # -----------------------------------------------------------------------------

    def add_action(
        self,
        action_id: str,
        action: "DevicePropertyActionItem" or "ChannelPropertyActionItem",
    ) -> None:
        if isinstance(action, DevicePropertyActionItem):
            self.__device_property_actions[action_id] = action

        elif isinstance(action, ChannelPropertyActionItem):
            self.__channel_property_actions[action_id] = action

    # -----------------------------------------------------------------------------

    def check_property_item(
        self, item: DevicePropertyItem or ChannelPropertyItem, value: str
    ) -> None:
        if isinstance(item, DevicePropertyItem):
            for condition in self.__device_property_conditions.values():
                if condition.device_property == item.key:
                    condition.validate(item, value)

            for action in self.__device_property_actions.values():
                if action.device_property == item.key:
                    action.validate(item, value)

        elif isinstance(item, ChannelPropertyItem):
            for condition in self.__channel_property_conditions.values():
                if condition.channel_property == item.key:
                    condition.validate(item, value)

            for action in self.__channel_property_actions.values():
                if action.channel_property == item.key:
                    action.validate(item, value)

        self.__check_fulfillment()
        self.__check_triggers()

    # -----------------------------------------------------------------------------

    def __check_fulfillment(self) -> None:
        self.__is_fulfilled = True

        for condition in self.__device_property_conditions.values():
            if condition.enabled and condition.is_fulfilled is False:
                self.__is_fulfilled = False

        for condition in self.__channel_property_conditions.values():
            if condition.enabled and condition.is_fulfilled is False:
                self.__is_fulfilled = False

    # -----------------------------------------------------------------------------

    def __check_triggers(self) -> None:
        self.__is_triggered = True

        for action in self.__device_property_actions.values():
            if action.enabled and action.is_triggered is False:
                self.__is_triggered = False

        for action in self.__channel_property_actions.values():
            if action.enabled and action.is_triggered is False:
                self.__is_triggered = False


#
# Property condition
#
# @package        FastyBird:MiniServer!
# @subpackage     Trigger
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class PropertyConditionItem(ABC):
    __condition_id: uuid.UUID
    __enabled: bool

    __operator: ConditionOperators
    __operand: str

    __device: str

    __is_fulfilled: bool = False

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        condition_id: uuid.UUID,
        enabled: bool,
        operator: ConditionOperators,
        operand: str,
        device: str,
    ) -> None:
        self.__condition_id = condition_id
        self.__enabled = enabled

        self.__operator = operator
        self.__operand = operand

        self.__device = device

        self.__is_fulfilled = False

    # -----------------------------------------------------------------------------

    @property
    def condition_id(self) -> uuid.UUID:
        return self.__condition_id

    # -----------------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self.__enabled

    # -----------------------------------------------------------------------------

    @property
    def operator(self) -> ConditionOperators:
        return self.__operator

    # -----------------------------------------------------------------------------

    @property
    def operand(self) -> str:
        return self.__operand

    # -----------------------------------------------------------------------------

    @property
    def is_fulfilled(self) -> bool:
        return self.__is_fulfilled

    # -----------------------------------------------------------------------------

    def validate(
        self, item: DevicePropertyItem or ChannelPropertyItem, value: str
    ) -> bool:
        normalized_value = PropertiesUtils.normalize_value(item, value)
        normalized_operand = PropertiesUtils.normalize_value(item, self.operand)

        # Reset actual status
        self.__is_fulfilled = False

        if self.__operator == ConditionOperators.OPERATOR_VALUE_EQUAL:
            self.__is_fulfilled = normalized_operand == normalized_value

        elif self.__operator == ConditionOperators.OPERATOR_VALUE_ABOVE:
            self.__is_fulfilled = normalized_operand < normalized_value

        elif self.__operator == ConditionOperators.OPERATOR_VALUE_BELOW:
            self.__is_fulfilled = normalized_operand > normalized_value

        return self.__is_fulfilled


#
# Device property condition
#
# @package        FastyBird:MiniServer!
# @subpackage     Trigger
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class DevicePropertyConditionItem(PropertyConditionItem):
    __device_property: str

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        condition_id: uuid.UUID,
        enabled: bool,
        operator: ConditionOperators,
        operand: str,
        device_property: str,
        device: str,
    ) -> None:
        super().__init__(condition_id, enabled, operator, operand, device)

        self.__device_property = device_property

    # -----------------------------------------------------------------------------

    @property
    def device_property(self) -> str:
        return self.__device_property

    # -----------------------------------------------------------------------------

    def validate(self, item: DevicePropertyItem, value: str) -> bool:
        return super().validate(item, value)


#
# Channel property condition
#
# @package        FastyBird:MiniServer!
# @subpackage     Trigger
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class ChannelPropertyConditionItem(PropertyConditionItem):
    __channel_property: str
    __channel: str

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        condition_id: uuid.UUID,
        enabled: bool,
        operator: ConditionOperators,
        operand: str,
        channel_property: str,
        channel: str,
        device: str,
    ) -> None:
        super().__init__(condition_id, enabled, operator, operand, device)

        self.__channel_property = channel_property
        self.__channel = channel

    # -----------------------------------------------------------------------------

    @property
    def channel_property(self) -> str:
        return self.__channel_property

    # -----------------------------------------------------------------------------

    def validate(self, item: ChannelPropertyItem, value: str) -> bool:
        return super().validate(item, value)


#
# Channel property action
#
# @package        FastyBird:MiniServer!
# @subpackage     Trigger
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class PropertyActionItem(ABC):
    __action_id: uuid.UUID
    __enabled: bool

    __value: str

    __device: str

    __is_triggered: bool = False

    # -----------------------------------------------------------------------------

    def __init__(
        self, action_id: uuid.UUID, enabled: bool, value: str, device: str
    ) -> None:
        self.__action_id = action_id
        self.__enabled = enabled

        self.__value = value

        self.__device = device

        self.__is_triggered = False

    # -----------------------------------------------------------------------------

    @property
    def action_id(self) -> uuid.UUID:
        return self.__action_id

    # -----------------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self.__enabled

    # -----------------------------------------------------------------------------

    @property
    def value(self) -> str:
        return self.__value

    # -----------------------------------------------------------------------------

    @property
    def is_triggered(self) -> bool:
        return self.__is_triggered

    # -----------------------------------------------------------------------------

    def validate(
        self, item: DevicePropertyItem or ChannelPropertyItem, value: str
    ) -> bool:
        if self.__value == "toggle":
            self.__is_triggered = False

        else:
            self.__is_triggered = PropertiesUtils.normalize_value(
                item, self.__value
            ) == PropertiesUtils.normalize_value(item, value)

        return self.__is_triggered


#
# Device property action
#
# @package        FastyBird:MiniServer!
# @subpackage     Trigger
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class DevicePropertyActionItem(PropertyActionItem):
    __device_property: str

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        action_id: uuid.UUID,
        enabled: bool,
        value: str,
        device_property: str,
        device: str,
    ) -> None:
        super().__init__(action_id, enabled, value, device)

        self.__device_property = device_property

    # -----------------------------------------------------------------------------

    @property
    def device_property(self) -> str:
        return self.__device_property

    # -----------------------------------------------------------------------------

    def validate(self, item: DevicePropertyItem, value: str) -> bool:
        return super().validate(item, value)


#
# Channel property action
#
# @package        FastyBird:MiniServer!
# @subpackage     Trigger
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class ChannelPropertyActionItem(PropertyActionItem):
    __channel_property: str
    __channel: str

    # -----------------------------------------------------------------------------

    def __init__(
        self,
        action_id: uuid.UUID,
        enabled: bool,
        value: str,
        channel_property: str,
        channel: str,
        device: str,
    ) -> None:
        super().__init__(action_id, enabled, value, device)

        self.__channel_property = channel_property
        self.__channel = channel

    # -----------------------------------------------------------------------------

    @property
    def channel_property(self) -> str:
        return self.__channel_property

    # -----------------------------------------------------------------------------

    def validate(self, item: ChannelPropertyItem, value: str) -> bool:
        return super().validate(item, value)


#
# Application triggers cache container
#
# @package        FastyBird:MiniServer!
# @subpackage     Trigger
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class TriggersCache:
    __triggers: List[TriggerItem]

    __iterator_index = 0

    # -----------------------------------------------------------------------------

    @orm.db_session
    def load(self) -> None:
        self.__triggers = []

        for trigger in TriggerEntity.select():
            trigger_cache = TriggerItem(trigger.trigger_id)

            if isinstance(trigger, AutomaticTriggerEntity):
                for condition in trigger.conditions:
                    if isinstance(condition, DevicePropertyConditionEntity):
                        trigger_cache.add_condition(
                            condition.condition_id.__str__(),
                            DevicePropertyConditionItem(
                                condition.condition_id,
                                condition.enabled,
                                condition.operator,
                                condition.operand,
                                condition.device_property,
                                condition.device,
                            ),
                        )

                    elif isinstance(condition, ChannelPropertyConditionEntity):
                        trigger_cache.add_condition(
                            condition.condition_id.__str__(),
                            ChannelPropertyConditionItem(
                                condition.condition_id,
                                condition.enabled,
                                condition.operator,
                                condition.operand,
                                condition.channel_property,
                                condition.channel,
                                condition.device,
                            ),
                        )

            for action in trigger.actions:
                if isinstance(action, ChannelPropertyActionEntity):
                    trigger_cache.add_action(
                        action.action_id.__str__(),
                        ChannelPropertyActionItem(
                            action.action_id,
                            action.enabled,
                            action.value,
                            action.channel_property,
                            action.channel,
                            action.device,
                        ),
                    )

            self.__triggers.append(trigger_cache)

    # -----------------------------------------------------------------------------

    def __iter__(self) -> "TriggersCache":
        return self

    # -----------------------------------------------------------------------------

    def __next__(self) -> TriggerItem:
        if self.__iterator_index < len(self.__triggers):
            result: TriggerItem = self.__triggers[self.__iterator_index]

            self.__iterator_index += 1

            return result

        # Reset index for nex iteration
        self.__iterator_index = 0

        # End of iteration
        raise StopIteration
