# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import os
import re
from collections.abc import Mapping, MutableMapping

from opentelemetry.propagators.textmap import Getter, Setter


def _normalize_key(key: str) -> str:
    if not key:
        return "_"
    result = re.sub(r"[^A-Za-z0-9_]", "_", key).upper()
    if result and result[0].isdigit():
        result = "_" + result
    return result


def _is_normalized_key(key: str) -> bool:
    if not key:
        return False
    if "0" <= key[0] <= "9":
        return False
    return all(
        "A" <= char <= "Z" or "0" <= char <= "9" or char == "_" for char in key
    )


class EnvironmentGetter(Getter[Mapping[str, str]]):
    """Getter implementation for extracting context and baggage from environment variables.

    EnvironmentGetter creates a lookup from the current environment variables
    whose names are already normalized at initialization time and provides
    simple data access without validation.

    Per the OpenTelemetry specification, environment variables are treated as immutable
    within a process. For environments where context-carrying environment variables
    change between logical requests (e.g., AWS Lambda's _X_AMZN_TRACE_ID), create a
    new EnvironmentGetter instance at the start of each request.

    Example usage:
        getter = EnvironmentGetter()
        traceparent = getter.get({}, "traceparent")
    """

    def __init__(self):
        # Per spec, Get reads only normalized environment variable names.
        self.carrier: dict[str, str] = {
            k: v for k, v in os.environ.items() if _is_normalized_key(k)
        }

    def get(self, carrier: Mapping[str, str], key: str) -> list[str] | None:
        """Get a value from the environment carrier for the given key.

        Args:
            carrier: Not used; maintained for interface compatibility with Getter[CarrierT]
            key: The key to look up (will be normalized)

        Returns:
            A list with a single string value if the key exists, None otherwise.
        """
        val = self.carrier.get(_normalize_key(key))
        if val is None:
            return None
        return [val]

    def keys(self, carrier: Mapping[str, str]) -> list[str]:
        """Get all keys from the environment carrier.

        Args:
            carrier: Not used; maintained for interface compatibility with Getter[CarrierT]

        Returns:
            List of all already-normalized environment variable keys.
        """
        return list(self.carrier.keys())


class EnvironmentSetter(Setter[MutableMapping[str, str]]):
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
        self, carrier: MutableMapping[str, str], key: str, value: str
    ) -> None:
        """Set a value in the carrier dictionary for the given key.

        Args:
            carrier: Dictionary to store environment variables
            key: The key to set (normalized)
            value: The value to set
        """
        carrier[_normalize_key(key)] = value
