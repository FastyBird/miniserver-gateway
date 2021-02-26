# -*- coding: utf-8 -*-

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

from setuptools import setup
from os import path

this_directory = path.abspath(path.dirname(__file__))

with open(path.join(this_directory, "readme.md"), encoding="utf-8") as f:
    long_description = f.read()

VERSION = "0.1.0"

setup(
    version=VERSION,
    name="miniserver-gateway",
    author="FastyBird",
    author_email="code@fastybird.com",
    license="Apache Software License (Apache Software License 2.0)",
    description="FastyBird MiniServer Gateway for IoT devices.",
    url="https://github.com/FastyBird/miniserver-gateway",
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    python_requires=">=3.5",
    packages=["miniserver_gateway", "miniserver_gateway.gateway", "miniserver_gateway.connectors",
              "miniserver_gateway.connectors.fb_bus", "miniserver_gateway.connectors.fb_bus.entities",
              "miniserver_gateway.connectors.fb_bus.handlers", "miniserver_gateway.connectors.fb_bus.transport",
              "miniserver_gateway.connectors.fb_bus.types", "miniserver_gateway.connectors.fb_bus.utilities",
              "miniserver_gateway.connectors.fb_mqtt_v1",
              "miniserver_gateway.db", "miniserver_gateway.events", "miniserver_gateway.exceptions",
              "miniserver_gateway.exchanges", "miniserver_gateway.exchanges.websockets",
              "miniserver_gateway.storages", "miniserver_gateway.triggers",
              "miniserver_gateway.utils",
              ],
    install_requires=[
        "pjon_cython",
        "pony",
        "PyYAML",
        "redis",
        "setuptools",
        "simplejson",
        "whistle"
    ],
    download_url="https://github.com/FastyBird/miniserver-gateway/archive/%s.tar.gz" % VERSION,
    entry_points={
        "console_scripts": [
            "miniserver-gateway = miniserver_gateway.fb_gateway:daemon"
        ]},
    package_data={
        "*": ["config/*"]
    })


