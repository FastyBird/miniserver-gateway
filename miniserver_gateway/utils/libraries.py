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
from os import path, listdir
from inspect import getmembers, isclass
from importlib import util
from logging import getLogger
from typing import Dict, List
from abc import ABCMeta

log = getLogger("libs")


#
# Libraries loaders utils
#
# @package        FastyBird:MiniServer!
# @subpackage     Utils
#
# @author         Adam Kadlec <adam.kadlec@fastybird.com>
#
class LibrariesUtils:
    # Buffer for imported modules
    # key - class name
    # value - loaded class
    loaded_connector_libraries: Dict[str, ABCMeta] = {}
    loaded_storage_libraries: Dict[str, ABCMeta] = {}
    loaded_exchange_libraries: Dict[str, ABCMeta] = {}

    # -----------------------------------------------------------------------------

    @staticmethod
    def check_and_import_connector(
        extension_type: str, module_name: str
    ) -> ABCMeta or None:
        if LibrariesUtils.loaded_connector_libraries.get(module_name) is None:
            base_dir: str = path.dirname(path.dirname(__file__))

            extensions_paths: List[str] = [
                path.abspath(
                    base_dir
                    + "/connectors/".replace("/", path.sep)
                    + extension_type.lower()
                ),
            ]

            extension_class = LibrariesUtils.load_module(module_name, extensions_paths)

            if extension_class is not None:
                # Save class into buffer
                LibrariesUtils.loaded_connector_libraries[module_name] = extension_class

                return extension_class

        else:
            log.debug("Class %s found in LibrariesUtils buffer.", module_name)

            return LibrariesUtils.loaded_connector_libraries[module_name]

        return None

    # -----------------------------------------------------------------------------

    @staticmethod
    def check_and_import_storage(module_name: str) -> ABCMeta or None:
        if LibrariesUtils.loaded_storage_libraries.get(module_name) is None:
            base_dir: str = path.dirname(path.dirname(__file__))

            extensions_paths: List[str] = [
                path.abspath(base_dir + "/storages/".replace("/", path.sep)),
            ]

            extension_class = LibrariesUtils.load_module(module_name, extensions_paths)

            if extension_class is not None:
                # Save class into buffer
                LibrariesUtils.loaded_storage_libraries[module_name] = extension_class

                return extension_class

        else:
            log.debug("Class %s found in LibrariesUtils buffer.", module_name)

            return LibrariesUtils.loaded_storage_libraries[module_name]

        return None

    # -----------------------------------------------------------------------------

    @staticmethod
    def check_and_import_exchange(module_name: str) -> ABCMeta or None:
        if LibrariesUtils.loaded_exchange_libraries.get(module_name) is None:
            base_dir: str = path.dirname(path.dirname(__file__))

            extensions_paths: List[str] = [
                path.abspath(base_dir + "/exchanges/".replace("/", path.sep)),
            ]

            extension_class = LibrariesUtils.load_module(module_name, extensions_paths)

            if extension_class is not None:
                # Save class into buffer
                LibrariesUtils.loaded_exchange_libraries[module_name] = extension_class

                return extension_class

        else:
            log.debug("Class %s found in LibrariesUtils buffer.", module_name)

            return LibrariesUtils.loaded_exchange_libraries[module_name]

        return None

    # -----------------------------------------------------------------------------

    @staticmethod
    def load_module(module_name: str, extensions_paths: List[str]) -> ABCMeta or None:
        try:
            for extension_path in extensions_paths:
                if path.exists(extension_path):
                    for file in listdir(extension_path):
                        if not file.startswith("__") and file.endswith(".py"):
                            try:
                                module_spec = util.spec_from_file_location(
                                    module_name, extension_path + path.sep + file
                                )

                                if module_spec is None:
                                    continue

                                module = util.module_from_spec(module_spec)

                                module_spec.loader.exec_module(module)

                                for extension_class in getmembers(module, isclass):
                                    if module_name in extension_class:
                                        log.debug(
                                            "Import %s from %s.",
                                            module_name,
                                            extension_path,
                                        )

                                        return extension_class[1]

                            except ImportError:
                                continue

                else:
                    log.error(
                        "Import %s failed, path %s doesn't exist",
                        module_name,
                        extension_path,
                    )

        except Exception as e:
            log.exception(e)

        return None

    # -----------------------------------------------------------------------------

    @staticmethod
    def install_package(package: str, version: str = "upgrade") -> bool:
        from sys import executable
        from subprocess import check_call, CalledProcessError

        result = False

        if version.lower() == "upgrade":
            try:
                result = check_call(
                    [executable, "-m", "pip", "install", package, "--upgrade", "--user"]
                )

            except CalledProcessError:
                result = check_call(
                    [executable, "-m", "pip", "install", package, "--upgrade"]
                )

        else:
            from pkg_resources import get_distribution

            current_package_version = None

            try:
                current_package_version = get_distribution(package)

            except Exception:
                pass

            if current_package_version is None or current_package_version != version:
                installation_sign = "==" if ">=" not in version else ""

                try:
                    result = check_call(
                        [
                            executable,
                            "-m",
                            "pip",
                            "install",
                            package + installation_sign + version,
                            "--user",
                        ]
                    )

                except CalledProcessError:
                    result = check_call(
                        [
                            executable,
                            "-m",
                            "pip",
                            "install",
                            package + installation_sign + version,
                        ]
                    )

        return result
