# Copyright The OpenTelemetry Authors
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

This is a configuration manager for OpenTelemetry. It reads configuration
values from environment variables prefixed with ``OPENTELEMETRY_PYTHON_`` whose
characters are only alphanumeric characters and unserscores, except for the
first character after ``OPENTELEMETRY_PYTHON_`` which must not be a number.

For example, these environment variables will be read:

1. ``OPENTELEMETRY_PYTHON_SOMETHING``
2. ``OPENTELEMETRY_PYTHON_SOMETHING_ELSE_``
3. ``OPENTELEMETRY_PYTHON_SOMETHING_ELSE_AND__ELSE``
4. ``OPENTELEMETRY_PYTHON_SOMETHING_ELSE_AND_else``
4. ``OPENTELEMETRY_PYTHON_SOMETHING_ELSE_AND_else2``

These won't:

1. ``OPENTELEMETRY_PYTH_SOMETHING``
2. ``OPENTELEMETRY_PYTHON_2_SOMETHING_AND__ELSE``
3. ``OPENTELEMETRY_PYTHON_SOMETHING_%_ELSE``

The values stored in the environment variables can be found in an instance of
``opentelemetry.configuration.Configuration``. This class can be instantiated
freely because instantiating it returns always the same object.

For example, if the environment variable
``OPENTELEMETRY_PYTHON_METER_PROVIDER`` value is ``my_meter_provider``, then
``Configuration().meter_provider == "my_meter_provider"`` would be ``True``.

Non defined attributes will always return ``None``. This is intended to make it
easier to use the ``Configuration`` object in actual code, because it won't be
necessary to check for the attribute to be defined first.

Environment variables used by OpenTelemetry
-------------------------------------------

1. OPENTELEMETRY_PYTHON_METER_PROVIDER
2. OPENTELEMETRY_PYTHON_TRACER_PROVIDER

The value of these environment variables should be the name of the entry point
that points to the class that implements either provider. This OpenTelemetry
API package provides one entry point for each, which can be found in the
setup.py file::

    entry_points={
        ...
        "opentelemetry_meter_provider": [
            "default_meter_provider = "
            "opentelemetry.metrics:DefaultMeterProvider"
        ],
        "opentelemetry_tracer_provider": [
            "default_tracer_provider = "
            "opentelemetry.trace:DefaultTracerProvider"
        ],
    }

To use the meter provider above, then the
``OPENTELEMETRY_PYTHON_METER_PROVIDER`` should be set to
"default_meter_provider" (this is not actually necessary since the
OpenTelemetry API provided providers are the default ones used if no
configuration is found in the environment variables).
"""

from os import environ
from re import fullmatch


class Configuration:
    _instance = None

    __slots__ = []

    def __new__(cls) -> "Configuration":
        if Configuration._instance is None:

            for key, value in environ.items():

                match = fullmatch(
                    r"OPENTELEMETRY_PYTHON_([A-Za-z_][\w_]*)", key
                )

                if match is not None:

                    key = match.group(1)

                    setattr(Configuration, "_{}".format(key), value)
                    setattr(
                        Configuration,
                        key,
                        property(
                            fget=lambda cls, key=key: getattr(
                                cls, "_{}".format(key)
                            )
                        ),
                    )

                Configuration.__slots__.append(key)

            Configuration.__slots__ = tuple(Configuration.__slots__)

            Configuration._instance = object.__new__(cls)

        return cls._instance

    def __getattr__(self, name):
        return None

    @classmethod
    def _reset(cls):
        """
        This method "resets" the global configuration attributes

        It is not intended to be used by production code but by testing code
        only.
        """
        cls.__slots__ = []
        cls._instance = None
