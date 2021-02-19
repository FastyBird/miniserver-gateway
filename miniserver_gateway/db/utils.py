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
import math


#
# Entity key generator
#
# @package        FastyBird:MiniServer!
# @subpackage     Database
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class EntityKeyHash:
    ALPHABET: str = "bcdfghjklmnpqrstvwxyz0123456789BCDFGHJKLMNPQRSTVWXYZ"

    BASE: int = len(ALPHABET)

    MAX_LEN: int = 6

    # -----------------------------------------------------------------------------

    @staticmethod
    def encode(
            n: int
    ) -> str:
        pad = EntityKeyHash.MAX_LEN - 1
        n = int(n + pow(EntityKeyHash.BASE, pad))

        s = []
        t = int(math.log(n, EntityKeyHash.BASE))

        while True:
            bcp = int(pow(EntityKeyHash.BASE, t))
            a = int(n / bcp) % EntityKeyHash.BASE
            s.append(EntityKeyHash.ALPHABET[a:a + 1])
            n = n - (a * bcp)
            t -= 1

            if t < 0:
                break

        return "".join(reversed(s))

    # -----------------------------------------------------------------------------

    @staticmethod
    def decode(
            n: str
    ) -> int:
        n = "".join(reversed(n))
        s = 0
        l = len(n) - 1
        t = 0

        while True:
            bcpow = int(pow(EntityKeyHash.BASE, l - t))
            s = s + EntityKeyHash.ALPHABET.index(n[t:t + 1]) * bcpow
            t += 1
            if t > l:
                break

        pad = EntityKeyHash.MAX_LEN - 1
        s = int(s - pow(EntityKeyHash.BASE, pad))

        return int(s)
