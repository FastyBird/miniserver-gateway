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

from os import path, listdir, mkdir, curdir
from miniserver_gateway.gateway.fb_gateway_service import FBGatewayService


def main() -> None:
    if "logs" not in listdir(curdir):
        mkdir("logs")

    FBGatewayService(path.dirname(path.abspath(__file__)) + "/config/fb_gateway.yaml".replace("/", path.sep))


def daemon() -> None:
    FBGatewayService("/etc/miniserver-gateway/config/fb_gateway.yaml".replace("/", path.sep))


if __name__ == "__main__":
    main()
