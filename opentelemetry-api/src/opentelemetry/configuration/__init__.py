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

from logging import getLogger
from os import environ

from pkg_resources import iter_entry_points

logger = getLogger(__name__)


class Configuration:
    _instance = None

    __slots__ = ("tracer_provider", "meter_provider")

    def __new__(cls) -> "Configuration":
        if Configuration._instance is None:

            configuration = {
                key: "default_{}".format(key) for key in cls.__slots__
            }

            for key, value in configuration.items():
                configuration[key] = environ.get(
                    "OPENTELEMETRY_PYTHON_{}".format(key.upper()), value
                )

            for key, value in configuration.items():
                underscored_key = "_{}".format(key)

                setattr(Configuration, underscored_key, None)
                setattr(
                    Configuration,
                    key,
                    property(
                        fget=lambda cls, local_key=key, local_value=value: cls._load(
                            key=local_key, value=local_value
                        )
                    ),
                )

            Configuration._instance = object.__new__(cls)

        return cls._instance

    @classmethod
    def _load(cls, key=None, value=None):
        underscored_key = "_{}".format(key)

        if getattr(cls, underscored_key) is None:
            try:
                setattr(
                    cls,
                    underscored_key,
                    next(
                        iter_entry_points(
                            "opentelemetry_{}".format(key), name=value,
                        )
                    ).load()(),
                )
            except Exception:  # pylint: disable=broad-except
                # FIXME Decide on how to handle this. Should an exception be
                # raised here, or only a message should be logged and should
                # we fall back to the default meter provider?
                logger.error(
                    "Failed to load configured provider %s", value,
                )
                raise

        return getattr(cls, underscored_key)
