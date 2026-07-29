# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Read view over declarative instrumentation configuration.

Implements the spec's ``ConfigProvider`` / ``ConfigProperties`` API
(``configuration/api.md``): a stateless, typed read view over the parsed
``instrumentation`` node of a declarative configuration, plus a global
``ConfigProvider`` that makes it retrievable by instrumentation code.

``ConfigProperties`` wraps a mapping (a parsed sub-tree of the config) and
exposes typed getters that return ``None`` when a key is absent or cannot
be coerced to the requested type, matching the spec's "return null" and
Java's ``DeclarativeConfigProperties`` semantics.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from logging import getLogger
from typing import Any

_logger = getLogger(__name__)


def _node_to_mapping(node: Any) -> dict[str, Any]:
    """Normalize a config node into a plain ``dict`` for typed access.

    Dataclass nodes (the parsed model tree) are converted recursively via
    ``asdict``; mappings are copied as-is. Anything else yields an empty
    mapping so the getters uniformly return ``None``.
    """
    if node is None:
        return {}
    if is_dataclass(node) and not isinstance(node, type):
        return asdict(node)
    if isinstance(node, Mapping):
        return dict(node)
    return {}


class ConfigProperties:
    """A typed read view over a parsed configuration sub-tree.

    Wraps a mapping of configuration keys to values. Typed getters coerce
    the stored value to the requested type and return ``None`` when the key
    is missing or the value has an incompatible type. ``get_config`` returns
    a nested :class:`ConfigProperties` for a sub-mapping, enabling traversal
    of the full instrumentation tree.
    """

    def __init__(self, properties: Mapping[str, Any] | None = None) -> None:
        self._properties: dict[str, Any] = (
            dict(properties) if properties is not None else {}
        )

    def get_string(self, name: str) -> str | None:
        """Return the value of ``name`` as a ``str``, or ``None``."""
        value = self._properties.get(name)
        return value if isinstance(value, str) else None

    def get_bool(self, name: str) -> bool | None:
        """Return the value of ``name`` as a ``bool``, or ``None``."""
        value = self._properties.get(name)
        return value if isinstance(value, bool) else None

    def get_int(self, name: str) -> int | None:
        """Return the value of ``name`` as an ``int``, or ``None``.

        ``bool`` values are rejected (they are not treated as integers).
        """
        value = self._properties.get(name)
        if isinstance(value, bool):
            return None
        return value if isinstance(value, int) else None

    def get_float(self, name: str) -> float | None:
        """Return the value of ``name`` as a ``float``, or ``None``.

        Accepts ``int`` values (widened to ``float``); rejects ``bool``.
        """
        value = self._properties.get(name)
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        return None

    def get_config(self, name: str) -> ConfigProperties | None:
        """Return the sub-mapping at ``name`` as :class:`ConfigProperties`.

        Returns ``None`` when ``name`` is absent or its value is not a
        mapping / dataclass node.
        """
        value = self._properties.get(name)
        if value is None:
            return None
        if is_dataclass(value) and not isinstance(value, type):
            return ConfigProperties(_node_to_mapping(value))
        if isinstance(value, Mapping):
            return ConfigProperties(dict(value))
        return None

    def get_config_list(self, name: str) -> list[ConfigProperties] | None:
        """Return the list at ``name`` as a list of :class:`ConfigProperties`.

        Each element must be a mapping / dataclass node; returns ``None``
        when ``name`` is absent or is not a list of mappings.
        """
        value = self._properties.get(name)
        if not isinstance(value, list):
            return None
        result: list[ConfigProperties] = []
        for item in value:
            mapping = _node_to_mapping(item)
            if not mapping and item is not None:
                return None
            result.append(ConfigProperties(mapping))
        return result

    def get_scalar_list(self, name: str, scalar_type: type) -> list | None:
        """Return the sequence at ``name`` as a list of ``scalar_type``.

        Elements whose type does not match ``scalar_type`` are dropped
        (matching Java's ``getScalarList``). ``bool`` is never treated as an
        ``int``. Returns ``None`` when ``name`` is absent or is not a list.
        """
        value = self._properties.get(name)
        if not isinstance(value, list):
            return None
        result: list = []
        for item in value:
            if scalar_type is int and isinstance(item, bool):
                continue
            if (
                scalar_type is float
                and isinstance(item, int)
                and not isinstance(item, bool)
            ):
                result.append(float(item))
                continue
            if isinstance(item, scalar_type):
                result.append(item)
        return result

    def keys(self) -> list[str]:
        """Return the property keys present in this view."""
        return list(self._properties.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._properties

    def __repr__(self) -> str:
        return f"ConfigProperties(keys={self.keys()!r})"


class ConfigProvider:
    """Holds the instrumentation :class:`ConfigProperties` for global access."""

    def __init__(self, instrumentation_config: ConfigProperties) -> None:
        self._instrumentation_config = instrumentation_config

    def get_instrumentation_config(self) -> ConfigProperties:
        """Return the read view over the ``instrumentation`` config node."""
        return self._instrumentation_config


_CONFIG_PROVIDER: ConfigProvider | None = None


def set_config_provider(config_provider: ConfigProvider) -> None:
    """Set the global :class:`ConfigProvider`.

    A warning is logged (and the value overwritten) if one is already set,
    matching the "set once" behavior of the other declarative globals.
    """
    global _CONFIG_PROVIDER  # pylint: disable=global-statement
    if _CONFIG_PROVIDER is not None:
        _logger.warning(
            "Overriding of current ConfigProvider is not allowed once set; "
            "overwriting the existing instance."
        )
    _CONFIG_PROVIDER = config_provider


def get_config_provider() -> ConfigProvider | None:
    """Return the global :class:`ConfigProvider`, or ``None`` if unset."""
    return _CONFIG_PROVIDER
