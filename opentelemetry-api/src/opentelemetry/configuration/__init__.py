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
5. ``OPENTELEMETRY_PYTHON_SOMETHING_ELSE_AND_else2``

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
``"default_meter_provider"`` (this is not actually necessary since the
OpenTelemetry API provided providers are the default ones used if no
configuration is found in the environment variables).

Configuration values that are exactly ``"True"`` or ``"False"`` will be
converted to its boolean values of ``True`` and ``False`` respectively.

Configuration values that can be casted to integers or floats will be casted.

This object can be used by any OpenTelemetry component, native or external.
For that reason, the ``Configuration`` object is designed to be immutable.
If a component would change the value of one of the ``Configuration`` object
attributes then another component that relied on that value may break, leading
to bugs that are very hard to debug. To avoid this situation, the preferred
approach for components that need a different value than the one provided by
the ``Configuration`` object is to implement a mechanism that allows the user
to override this value instead of changing it.
"""

from os import environ
from re import fullmatch
from typing import ClassVar, Dict, Optional, TypeVar, Union

ConfigValue = Union[str, bool, int, float]
_T = TypeVar("_T", ConfigValue, Optional[ConfigValue])


class Configuration:
    _instance = None  # type: ClassVar[Optional[Configuration]]
    _config_map = {}  # type: ClassVar[Dict[str, ConfigValue]]

    def __new__(cls) -> "Configuration":
        if cls._instance is not None:
            instance = cls._instance
        else:

            instance = super().__new__(cls)
            for key, value_str in environ.items():

                match = fullmatch(
                    r"OPENTELEMETRY_PYTHON_([A-Za-z_][\w_]*)", key
                )

                if match is not None:

                    key = match.group(1)
                    value = value_str  # type: ConfigValue

                    if value_str == "True":
                        value = True
                    elif value_str == "False":
                        value = False
                    else:
                        try:
                            value = int(value_str)
                        except ValueError:
                            pass
                        try:
                            value = float(value_str)
                        except ValueError:
                            pass

                    instance._config_map[key] = value

            cls._instance = instance

        return instance

    def __getattr__(self, name: str) -> Optional[ConfigValue]:
        return self._config_map.get(name)

    def __setattr__(self, key: str, val: ConfigValue) -> None:
        if key == "_config_map":
            super().__setattr__(key, val)
        else:
            raise AttributeError(key)

    def get(self, name: str, default: _T) -> _T:
        """Use this typed method for dynamic access instead of `getattr`

        :rtype: str or bool or int or float or None
        """
        val = self._config_map.get(name, default)
        return val

    @classmethod
    def _reset(cls) -> None:
        """
        This method "resets" the global configuration attributes

        It is not intended to be used by production code but by testing code
        only.
        """

        if cls._instance:
            cls._instance._config_map.clear()  # pylint: disable=protected-access
            cls._instance = None
