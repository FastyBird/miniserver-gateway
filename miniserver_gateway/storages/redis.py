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
import json
from redis import Redis
from typing import Dict

# App libs
from miniserver_gateway.db.cache import DevicePropertyItem, ChannelPropertyItem
from miniserver_gateway.storages.storages import log, StorageInterface, StorageItem
from miniserver_gateway.utils.properties import PropertiesUtils


#
# Redis data storage settings
#
# @package        FastyBird:MiniServer!
# @subpackage     Storage
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class RedisStorageSettings:
    __host: str = "127.0.0.1"
    __port: int = 6379
    __username: str or None = None
    __password: str or None = None

    # -----------------------------------------------------------------------------

    def __init__(self, config: dict) -> None:
        self.__host = config.get("host", "127.0.0.1")
        self.__port = int(config.get("port", 6379))
        self.__username = config.get("username", None)
        self.__password = config.get("password", None)

    # -----------------------------------------------------------------------------

    @property
    def host(self) -> str:
        return self.__host

    # -----------------------------------------------------------------------------

    @property
    def port(self) -> int:
        return self.__port

    # -----------------------------------------------------------------------------

    @property
    def username(self) -> str or None:
        return self.__username

    # -----------------------------------------------------------------------------

    @property
    def password(self) -> str or None:
        return self.__password


#
# Redis data storage
#
# @package        FastyBird:MiniServer!
# @subpackage     Storage
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class RedisStorage(StorageInterface):
    __redis_client: Redis

    __settings: RedisStorageSettings

    __data_cache: Dict[str, StorageItem] = {}

    # -----------------------------------------------------------------------------

    def __init__(self, config: dict) -> None:
        super().__init__(config)

        self.__settings = RedisStorageSettings(config)

        self.__redis_client = Redis(host=self.__settings.host, port=self.__settings.port)

    # -----------------------------------------------------------------------------

    def close(self) -> None:
        pass

    # -----------------------------------------------------------------------------

    def clear_cache(self) -> None:
        self.__data_cache = {}

    # -----------------------------------------------------------------------------

    def write_property_value(
        self,
        item: DevicePropertyItem or ChannelPropertyItem,
        value_to_write: int or float or str or bool or None,
    ) -> bool:
        storage_key: str = item.property_id.__str__()

        stored_data: StorageItem or None = self.read_property_data(item)

        if (
            stored_data is None
            or stored_data.value is None
            or value_to_write != stored_data.value
            or stored_data.is_pending
        ):
            data_to_write = {
                "id": item.property_id.__str__(),
                "value": value_to_write,
                "expected": None,
                "pending": False,
            }

            if stored_data is not None and stored_data.expected is not None:
                # Check if received value is as expected if is set
                if stored_data.expected != data_to_write.get("value"):
                    data_to_write["pending"] = True
                    data_to_write["expected"] = stored_data.expected

                else:
                    data_to_write["pending"] = False
                    data_to_write["expected"] = None

            if self.__store_into_storage(storage_key, json.dumps(data_to_write)):
                log.debug(
                    "Successfully written value for property: {} with value: {}".format(
                        storage_key, data_to_write.get("value")
                    )
                )

                self.__data_cache[storage_key] = StorageItem(
                    value=data_to_write.get("value"),
                    expected=data_to_write.get("expected"),
                    pending=data_to_write.get("pending"),
                )

                return True

        return False

    # -----------------------------------------------------------------------------

    def write_property_expected(
        self,
        item: DevicePropertyItem or ChannelPropertyItem,
        expected_value_to_write: int or float or str or bool or None,
    ) -> bool:
        storage_key: str = item.property_id.__str__()

        stored_data: StorageItem or None = self.read_property_data(item)

        if stored_data is None or stored_data.value is None or expected_value_to_write != stored_data.value:
            data_to_write = {
                "id": item.property_id.__str__(),
                "value": stored_data.value if stored_data is not None else None,
                "expected": expected_value_to_write,
                "pending": True,
            }

            if self.__store_into_storage(storage_key, json.dumps(data_to_write)):
                log.debug("Successfully written expected value for property: {}".format(storage_key))

                self.__data_cache[storage_key] = StorageItem(
                    value=data_to_write.get("value"),
                    expected=data_to_write.get("expected"),
                    pending=data_to_write.get("pending"),
                )

                return True

        return False

    # -----------------------------------------------------------------------------

    def read_property_value(
        self, item: DevicePropertyItem or ChannelPropertyItem
    ) -> int or float or str or bool or None:
        stored_data = self.read_property_data(item)

        if stored_data is not None:
            return stored_data.value

        return None

    # -----------------------------------------------------------------------------

    def read_property_expected(
        self, item: DevicePropertyItem or ChannelPropertyItem
    ) -> int or float or str or bool or None:
        stored_data = self.read_property_data(item)

        if stored_data is not None:
            return stored_data.expected

        return None

    # -----------------------------------------------------------------------------

    def read_property_data(self, item: DevicePropertyItem or ChannelPropertyItem) -> StorageItem or None:
        storage_key: str = item.property_id.__str__()

        if storage_key in self.__data_cache:
            return self.__data_cache[storage_key]

        stored_data = self.__redis_client.get(storage_key)

        if stored_data is None:
            return None

        if isinstance(stored_data, bytes):
            stored_data = stored_data.decode("utf-8")

        try:
            stored_data_dict: dict = json.loads(stored_data)

            if "value" in stored_data_dict and "expected" in stored_data_dict and "pending" in stored_data_dict:
                self.__data_cache[storage_key] = StorageItem(
                    value=PropertiesUtils.normalize_value(item, stored_data_dict.get("value", None)),
                    expected=PropertiesUtils.normalize_value(item, stored_data_dict.get("expected", None)),
                    pending=bool(stored_data_dict.get("pending", False)),
                )

                return self.__data_cache[storage_key]

            # Stored data are not valid, we will remove them from storages
            self.__redis_client.delete(storage_key)

        except TypeError as e:
            # Stored value is invalid, key should be removed
            self.__redis_client.delete(storage_key)
            del self.__data_cache[storage_key]

            log.error(
                "Property data for property: {} could not be loaded from storages. Data type error".format(storage_key)
            )
            log.exception(e)

        except json.JSONDecodeError as e:
            # Stored value is invalid, key should be removed
            self.__redis_client.delete(storage_key)
            del self.__data_cache[storage_key]

            log.error(
                "Property data for property: {} could not be loaded from storages. Json error".format(storage_key)
            )
            log.exception(e)

        return None

    # -----------------------------------------------------------------------------

    def __store_into_storage(self, key: str, content: str) -> bool:
        return self.__redis_client.set(key, content)
