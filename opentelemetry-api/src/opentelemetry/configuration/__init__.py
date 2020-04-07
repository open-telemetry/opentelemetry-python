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

This is a configuration manager for the Tracer and Meter providers. It reads
configuration from environment variables prefixed with
``OPENTELEMETRY_PYTHON_``:

1. ``OPENTELEMETRY_PYTHON_TRACER_PROVIDER``
2. ``OPENTELEMETRY_PYTHON_METER_PROVIDER``

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

Once this is done, the configuration manager can be used by simply importing
it from opentelemetry.configuration.Configuration. This is a class that can
be instantiated as many times as needed without concern because it will
always produce the same instance. Its attributes are lazy loaded and they
hold an instance of their corresponding provider. So, for example, to get
the configured meter provider::

    from opentelemetry.configuration import Configuration

    tracer_provider = Configuration().tracer_provider

"""

from os import environ
from re import fullmatch


class Configuration:
    _instance = None

    __slots__ = []

    def __new__(cls) -> "Configuration":
        if Configuration._instance is None:

            for key, value in environ.items():

                match = fullmatch("OPENTELEMETRY_PYTHON_([A-Z][A-Z_]*)", key)

                if match is not None:

                    key = match.group(1).lower()

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
