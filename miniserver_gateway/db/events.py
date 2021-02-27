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
from abc import ABC
from enum import Enum, unique
from pony.orm import core as orm
from whistle import Event

# App libs
from miniserver_gateway.types.types import ModulesOrigins


#
# Action types
#
# @package        FastyBird:MiniServer!
# @subpackage     Database
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
@unique
class EntityChangedType(Enum):
    ENTITY_CREATED: str = "created"
    ENTITY_UPDATED: str = "updated"
    ENTITY_DELETED: str = "deleted"


#
# Database has updated entity
#
# @package        FastyBird:MiniServer!
# @subpackage     Database
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class DatabaseEntityChangedEvent(ABC, Event):
    __origin: ModulesOrigins
    __entity: orm.Entity
    __action_type: EntityChangedType

    EVENT_NAME: str = "database.entityChanged"

    # -----------------------------------------------------------------------------

    def __init__(self, origin: ModulesOrigins, entity: orm.Entity, action_type: EntityChangedType) -> None:
        self.__origin = origin
        self.__entity = entity
        self.__action_type = action_type

    # -----------------------------------------------------------------------------

    @property
    def origin(self) -> ModulesOrigins:
        return self.__origin

    # -----------------------------------------------------------------------------

    @property
    def entity(self) -> orm.Entity:
        return self.__entity

    # -----------------------------------------------------------------------------

    @property
    def action_type(self) -> EntityChangedType:
        return self.__action_type
