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

import os
import typing

from opentelemetry.propagators.textmap import Getter, Setter


class EnvironmentGetter(Getter[dict]):
    """Getter implementation for extracting context and baggage from environment variables.

    EnvironmentGetter creates a case-insensitive lookup from the current environment
    variables and provides simple data access without validation.

    Example usage:
        getter = EnvironmentGetter()
        traceparent = getter.get({}, "traceparent")
    """

    def __init__(self):
        # Create case-insensitive lookup from current environment
        self.carrier = {k.lower(): v for k, v in os.environ.items()}

    def get(
        self, carrier: dict, key: str
    ) -> typing.Optional[typing.List[str]]:
        """Get a value from the environment for the given key.

        Args:
            carrier: Not used for environment getter, maintained for interface compatibility
            key: The key to look up (case-insensitive)

        Returns:
            A list with a single string value if the key exists, None otherwise.
        """
        val = self.carrier.get(key.lower())
        if val is None:
            return None
        if isinstance(val, typing.Iterable) and not isinstance(val, str):
            return list(val)
        return [val]

    def keys(self, carrier: dict) -> typing.List[str]:
        """Get all keys from the environment carrier.

        Args:
            carrier: Not used for environment getter, maintained for interface compatibility

        Returns:
            List of all environment variable keys (lowercase).
        """
        return list(self.carrier.keys())


class EnvironmentSetter(Setter[dict]):
    """Setter implementation for building environment variable dictionaries.

    EnvironmentSetter builds a dictionary of environment variables that
    can be passed to utilities like subprocess.run()

    Example usage:
        setter = EnvironmentSetter()
        env_vars = {}
        setter.set(env_vars, "traceparent", "00-trace-id-span-id-01")
        subprocess.run(myCommand, env=env_vars)
    """

    def set(
        self, carrier: typing.Optional[dict], key: str, value: str
    ) -> None:
        """Set a value in the carrier dictionary for the given key.

        Args:
            carrier: Dictionary to store environment variables, created if None
            key: The key to set (will be converted to uppercase)
            value: The value to set
        """
        if carrier is None:
            carrier = {}
        carrier[key.upper()] = value
