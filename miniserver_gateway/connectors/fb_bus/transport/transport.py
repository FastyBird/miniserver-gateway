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
from abc import ABC, abstractmethod


#
# FastyBird bus transport service interface
#
# @package        FastyBird:MiniServer!
# @subpackage     Connectors
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class TransportInterface(ABC):
    @abstractmethod
    def broadcast_packet(self, payload: list, waiting_time: float = 0.0) -> bool:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def send_packet(self, address: int, payload: list, waiting_time: float = 0.0) -> bool:
        pass

    # -----------------------------------------------------------------------------

    @abstractmethod
    def run(self) -> int:
        pass
