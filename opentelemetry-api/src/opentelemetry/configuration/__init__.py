# Copyright 2020, OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# FIXME find a better way to avoid all those "Expression has type "Any"" errors
# type: ignore

"""
Simple configuration manager

This configuration manager reads configuration values from a JSON file, the
values read there can be overriden by environment variables.

It would probably be better to replace this configuration manager with a more
powerful one, Dynaconf, for example.
"""

from json import load
from os import environ
from os.path import exists, join
from pathlib import Path


class Configuration:
    _instance = None

    __slots__ = ["tracer_provider", "meter_provider"]

    def __new__(cls) -> "Configuration":
        if Configuration._instance is None:

            configuration = {
                key: "default_{}".format(key) for key in cls.__slots__
            }

            configuration_file_path = join(
                Path.home(), ".config", "opentelemetry_python.json"
            )

            if exists(configuration_file_path):

                with open(configuration_file_path) as configuration_file:
                    file_configuration = load(configuration_file)

                for key, value in configuration.items():
                    configuration[key] = file_configuration.get(key, value)

            for key, value in configuration.items():
                configuration[key] = environ.get(
                    "OPENTELEMETRY_PYTHON_{}".format(key.upper()), value
                )

            for key, value in configuration.items():
                underscored_key = "_{}".format(key)

                setattr(Configuration, underscored_key, value)
                setattr(
                    Configuration,
                    key,
                    property(
                        (
                            lambda underscored_key: lambda self: getattr(
                                self, underscored_key
                            )
                        )(underscored_key)
                    ),
                )

            Configuration._instance = object.__new__(cls)

        return cls._instance
