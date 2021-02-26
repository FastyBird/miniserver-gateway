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
import logging
import time
from threading import Thread
from queue import Queue, Full as QueueFull

# App libs
from miniserver_gateway.constants import LOG_LEVEL
from miniserver_gateway.events.dispatcher import app_dispatcher
from miniserver_gateway.connectors.events import ConnectorPropertyValueEvent
from miniserver_gateway.db.cache import (
    device_property_cache,
    channel_property_cache,
    DevicePropertyItem,
    ChannelPropertyItem,
)
from miniserver_gateway.triggers.cache import (
    TriggersCache,
    DevicePropertyActionItem,
    ChannelPropertyActionItem,
)
from miniserver_gateway.triggers.events import TriggerActionFiredEvent
from miniserver_gateway.triggers.queue import FireTriggerActionQueueItem

logging.basicConfig(level=LOG_LEVEL)
log = logging.getLogger("triggers")


#
# Triggers watcher
#
# @package        FastyBird:MiniServer!
# @subpackage     Trigger
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class Trigger(Thread):
    __stopped: bool = False

    __triggers: TriggersCache

    # -----------------------------------------------------------------------------

    def __init__(self) -> None:
        Thread.__init__(self)

        app_dispatcher.add_listener(
            ConnectorPropertyValueEvent.EVENT_NAME, self.__check_connector_value_event
        )

        # Queue for consuming incoming data from connectors
        self.__queue = Queue(maxsize=1000)

        # Initialize all triggers
        self.__triggers = TriggersCache()
        self.__triggers.load()

        # Threading config...
        self.setDaemon(True)
        self.setName("Triggers watcher thread")
        # ...and starting
        self.start()

    # -----------------------------------------------------------------------------

    def run(self) -> None:
        self.__stopped = False

        while True:
            if not self.__queue.empty():
                record = self.__queue.get()

                if isinstance(record, FireTriggerActionQueueItem):
                    self.__process_trigger_record(record)

            # All records have to be processed before thread is closed
            if self.__stopped and self.__queue.empty():
                break

            time.sleep(0.001)

    # -----------------------------------------------------------------------------

    def close(self) -> None:
        self.__stopped = True

    # -----------------------------------------------------------------------------

    def __check_connector_value_event(self, event: ConnectorPropertyValueEvent) -> None:
        if isinstance(event.record, DevicePropertyItem) or isinstance(
            event.record, ChannelPropertyItem
        ):
            if (
                event.previous_value is not None
                and event.previous_value == event.actual_value
            ):
                return

            for trigger in self.__triggers:
                trigger.check_property_item(event.record, str(event.actual_value))

                if trigger.is_fulfilled and not trigger.is_triggered:
                    try:
                        for action in trigger.actions.values():
                            self.__queue.put(
                                FireTriggerActionQueueItem(trigger, action)
                            )

                    except QueueFull:
                        log.error(
                            "Triggers processing queue is full. New messages could not be added"
                        )

    # -----------------------------------------------------------------------------

    @staticmethod
    def __process_trigger_record(record: FireTriggerActionQueueItem) -> None:
        action = record.action

        if not action.enabled:
            return

        if isinstance(action, DevicePropertyActionItem):
            property_item = device_property_cache.get_property_by_key(
                action.device_property
            )

            if property_item is not None:
                app_dispatcher.dispatch(
                    TriggerActionFiredEvent.EVENT_NAME,
                    TriggerActionFiredEvent(property_item, action.value),
                )

                log.debug("Triggering trigger action for device property")

        elif isinstance(action, ChannelPropertyActionItem):
            property_item = channel_property_cache.get_property_by_key(
                action.channel_property
            )

            if property_item is not None:
                app_dispatcher.dispatch(
                    TriggerActionFiredEvent.EVENT_NAME,
                    TriggerActionFiredEvent(property_item, action.value),
                )

                log.debug("Triggering trigger action for channel property")
