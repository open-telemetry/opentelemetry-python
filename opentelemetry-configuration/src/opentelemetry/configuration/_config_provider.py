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

from opentelemetry.util._once import Once

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

    def _log_type_mismatch(self, name: str, value: Any, expected: str) -> None:
        _logger.warning(
            "Config property %r has type %s, expected %s; ignoring.",
            name,
            type(value).__name__,
            expected,
        )

    @staticmethod
    def _as_string(value: Any) -> str | None:
        return value if isinstance(value, str) else None

    @staticmethod
    def _as_bool(value: Any) -> bool | None:
        return value if isinstance(value, bool) else None

    @staticmethod
    def _as_int(value: Any) -> int | None:
        # ``bool`` is a subclass of ``int`` in Python but is not an integer
        # value for config purposes, so it is rejected.
        if isinstance(value, bool):
            return None
        return value if isinstance(value, int) else None

    @staticmethod
    def _as_float(value: Any) -> float | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        return None

    def get_string(self, name: str) -> str | None:
        """Return the value of ``name`` as a ``str``, or ``None``.

        Logs a warning if ``name`` is present with an incompatible type.
        """
        value = self._properties.get(name)
        result = self._as_string(value)
        if result is None and value is not None:
            self._log_type_mismatch(name, value, "string")
        return result

    def get_bool(self, name: str) -> bool | None:
        """Return the value of ``name`` as a ``bool``, or ``None``.

        Logs a warning if ``name`` is present with an incompatible type.
        """
        value = self._properties.get(name)
        result = self._as_bool(value)
        if result is None and value is not None:
            self._log_type_mismatch(name, value, "bool")
        return result

    def get_int(self, name: str) -> int | None:
        """Return the value of ``name`` as an ``int``, or ``None``.

        ``bool`` values are rejected (they are not treated as integers). Logs
        a warning if ``name`` is present with an incompatible type.
        """
        value = self._properties.get(name)
        result = self._as_int(value)
        if result is None and value is not None:
            self._log_type_mismatch(name, value, "int")
        return result

    def get_float(self, name: str) -> float | None:
        """Return the value of ``name`` as a ``float``, or ``None``.

        Accepts ``int`` values (widened to ``float``); rejects ``bool``. Logs
        a warning if ``name`` is present with an incompatible type.
        """
        value = self._properties.get(name)
        result = self._as_float(value)
        if result is None and value is not None:
            self._log_type_mismatch(name, value, "float")
        return result

    def get_config(self, name: str) -> ConfigProperties | None:
        """Return the sub-mapping at ``name`` as :class:`ConfigProperties`.

        Returns ``None`` when ``name`` is absent or its value is not a
        mapping / dataclass node. Logs a warning if ``name`` is present with an
        incompatible type.
        """
        value = self._properties.get(name)
        if value is None:
            return None
        if is_dataclass(value) and not isinstance(value, type):
            return ConfigProperties(_node_to_mapping(value))
        if isinstance(value, Mapping):
            return ConfigProperties(dict(value))
        self._log_type_mismatch(name, value, "mapping")
        return None

    def get_config_list(self, name: str) -> list[ConfigProperties] | None:
        """Return the list at ``name`` as a list of :class:`ConfigProperties`.

        Each element must be a mapping / dataclass node; returns ``None``
        when ``name`` is absent or is not a list of mappings. Logs a warning if
        ``name`` is present with an incompatible type.
        """
        value = self._properties.get(name)
        if value is None:
            return None
        if not isinstance(value, list):
            self._log_type_mismatch(name, value, "list of mappings")
            return None
        result: list[ConfigProperties] = []
        for item in value:
            mapping = _node_to_mapping(item)
            if not mapping and item is not None:
                self._log_type_mismatch(name, value, "list of mappings")
                return None
            result.append(ConfigProperties(mapping))
        return result

    def get_string_list(self, name: str) -> list[str] | None:
        """Return the sequence at ``name`` as a list of ``str``.

        Elements with an incompatible type are dropped. Returns ``None`` when
        ``name`` is absent or is not a sequence.
        """
        return self._scalar_list(name, self._as_string)

    def get_bool_list(self, name: str) -> list[bool] | None:
        """Return the sequence at ``name`` as a list of ``bool``.

        Elements with an incompatible type are dropped. Returns ``None`` when
        ``name`` is absent or is not a sequence.
        """
        return self._scalar_list(name, self._as_bool)

    def get_int_list(self, name: str) -> list[int] | None:
        """Return the sequence at ``name`` as a list of ``int``.

        Elements with an incompatible type (including ``bool``) are dropped.
        Returns ``None`` when ``name`` is absent or is not a sequence.
        """
        return self._scalar_list(name, self._as_int)

    def get_float_list(self, name: str) -> list[float] | None:
        """Return the sequence at ``name`` as a list of ``float``.

        ``int`` elements are widened to ``float``; incompatible elements are
        dropped. Returns ``None`` when ``name`` is absent or is not a sequence.
        """
        return self._scalar_list(name, self._as_float)

    def _scalar_list(self, name: str, coerce) -> list | None:
        value = self._properties.get(name)
        if value is None:
            return None
        if not isinstance(value, list):
            self._log_type_mismatch(name, value, "list of scalars")
            return None
        result: list = []
        for item in value:
            coerced = coerce(item)
            if coerced is not None:
                result.append(coerced)
        return result

    def keys(self) -> set[str]:
        """Return the set of property keys present in this view."""
        return set(self._properties.keys())

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


class NoOpConfigProvider(ConfigProvider):
    """A :class:`ConfigProvider` exposing empty instrumentation config.

    Mirrors ``NoOpTracerProvider`` and Java's ``ConfigProvider.noop()`` — an
    explicit no-op for callers that want an empty provider.
    """

    def __init__(self) -> None:
        super().__init__(ConfigProperties())


class ProxyConfigProvider(ConfigProvider):
    """A :class:`ConfigProvider` that defers to the global provider.

    Returned by :func:`get_config_provider` before a real provider has been
    set. It reads the global provider lazily on each call, so a caller that
    obtains the provider early still sees configuration installed later —
    mirroring ``ProxyTracerProvider`` / ``ProxyLoggerProvider``. Until a real
    provider is set, it exposes empty instrumentation config.
    """

    def __init__(self) -> None:
        super().__init__(ConfigProperties())

    def get_instrumentation_config(self) -> ConfigProperties:
        if _CONFIG_PROVIDER is not None:
            return _CONFIG_PROVIDER.get_instrumentation_config()
        return super().get_instrumentation_config()


_CONFIG_PROVIDER_SET_ONCE = Once()
_CONFIG_PROVIDER: ConfigProvider | None = None
_PROXY_CONFIG_PROVIDER = ProxyConfigProvider()


def set_config_provider(config_provider: ConfigProvider) -> None:
    """Set the global :class:`ConfigProvider`.

    This can only be done once; a warning is logged on any further attempt and
    the existing provider is kept, matching the set-once behavior of the other
    OpenTelemetry globals (e.g. :func:`opentelemetry.trace.set_tracer_provider`).
    """

    def set_cp() -> None:
        global _CONFIG_PROVIDER  # pylint: disable=global-statement
        _CONFIG_PROVIDER = config_provider

    did_set = _CONFIG_PROVIDER_SET_ONCE.do_once(set_cp)

    if not did_set:
        _logger.warning("Overriding of current ConfigProvider is not allowed")


def get_config_provider() -> ConfigProvider:
    """Return the global :class:`ConfigProvider`.

    Returns a :class:`ProxyConfigProvider` when none has been set, so callers
    never receive ``None`` and a provider obtained before
    :func:`set_config_provider` still resolves to the one installed later.
    """
    if _CONFIG_PROVIDER is None:
        return _PROXY_CONFIG_PROVIDER
    return _CONFIG_PROVIDER
