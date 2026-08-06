# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Recursive dict-to-dataclass conversion for parsed config data.

The YAML/JSON loader produces nested dicts. Factory functions expect typed
dataclass instances (e.g. ``TracerProvider``, ``SpanProcessor``). This module
walks each field's type annotation and converts nested dicts into their
corresponding dataclass types.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import MISSING, fields, is_dataclass
from enum import Enum
from types import UnionType
from typing import Any, TypeVar, Union, get_args, get_origin, get_type_hints

_T = TypeVar("_T")


def _unwrap_optional(type_hint: Any) -> Any:
    """Strip ``None`` from a ``X | None`` / ``Optional[X]`` annotation.

    Returns the unwrapped type, or the original hint if not a union with None.
    """
    origin = get_origin(type_hint)
    if origin is UnionType or origin is Union:
        non_none = [t for t in get_args(type_hint) if t is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return type_hint


def _is_empty_constructible_dataclass(unwrapped: Any) -> bool:
    """True if ``unwrapped`` is a dataclass type instantiable with no args.

    A dataclass with only optional fields (all have a default or
    default_factory) can be built as ``cls()``; one with a required field
    cannot, and coercing a present null into it would raise ``TypeError``.
    """
    return (
        isinstance(unwrapped, type)
        and is_dataclass(unwrapped)
        and all(
            field.default is not MISSING
            or field.default_factory is not MISSING
            for field in fields(unwrapped)
        )
    )


def _convert_value(value: Any, type_hint: Any) -> Any:
    """Convert a value according to its type hint.

    Recursively converts dicts to dataclasses and lists of dicts to lists of
    dataclasses. Other values (primitives, enums, ``dict[str, Any]`` aliases)
    pass through unchanged.
    """
    unwrapped = _unwrap_optional(type_hint)
    origin = get_origin(unwrapped)

    if value is None:
        # A mapping key present with an empty (null) YAML value parses to
        # ``None``, which is otherwise indistinguishable from an absent key.
        # For object-typed nodes the declarative-config spec treats a present
        # null as "select this with an empty config" — e.g. ``always_on:`` is
        # equivalent to ``always_on: {}`` and a metric ``console:`` exporter to
        # ``console: {}``. Substitute an empty mapping and let the dict/
        # dataclass handling below build it, so downstream ``is not None`` type
        # dispatch selects it. Scalar fields — and dataclasses with required
        # fields, which cannot be defaulted — keep ``None``, so an absent
        # optional section stays unset.
        if origin is dict or _is_empty_constructible_dataclass(unwrapped):
            value = {}
        else:
            return None

    # list[X] — recurse on each element
    if origin is list and isinstance(value, list):
        args = get_args(unwrapped)
        if args:
            item_type = args[0]
            return [_convert_value(item, item_type) for item in value]
        return value

    # Direct dataclass type — recurse
    if (
        isinstance(unwrapped, type)
        and is_dataclass(unwrapped)
        and isinstance(value, dict)
    ):
        return _dict_to_dataclass(value, unwrapped)

    # Enum type — coerce string/value to the Enum member
    if (
        isinstance(unwrapped, type)
        and issubclass(unwrapped, Enum)
        and not isinstance(value, unwrapped)
    ):
        return unwrapped(value)

    return value


def _dict_to_dataclass(data: Mapping[str, Any], cls: type[_T]) -> _T:
    """Recursively convert a mapping to a dataclass instance.

    For each key in ``data``:
    - If it matches a known dataclass field, the value is converted according
      to that field's type annotation (recursing for nested dataclasses).
    - Unknown keys are passed through as kwargs; classes decorated with
      ``@_additional_properties`` will capture them on the instance's
      ``additional_properties`` attribute.

    ``ClassVar`` fields (e.g. the ``additional_properties`` annotation on
    decorated dataclasses) are ignored as expected.

    Raises:
        TypeError: If ``cls`` is not a dataclass type.
    """
    if not is_dataclass(cls):
        raise TypeError(f"{cls.__name__} is not a dataclass")

    # Annotated as ``dict[str, Any]`` so astroid stops tracing into
    # ``get_type_hints`` — under pylint 3.x that path leads into
    # Python 3.14's ``annotationlib`` (which uses t-strings) and crashes.
    hints: dict[str, Any] = dict(get_type_hints(cls, include_extras=False))
    known_fields = {f.name for f in fields(cls)}
    kwargs: dict[str, Any] = {}

    for key, value in data.items():
        # The OTel configuration schema uses "/" as a namespace separator for
        # development/experimental features (e.g. "otlp_file/development",
        # "instrumentation/development").  Python identifiers cannot contain
        # "/", so the corresponding dataclass fields use "_" instead (e.g.
        # "otlp_file_development").  Without this normalisation the key would
        # not match any known field and would fall through to
        # additional_properties, causing the factory lookup to fail silently.
        field_key = key.replace("/", "_")
        if field_key in known_fields:
            type_hint = hints.get(field_key)
            kwargs[field_key] = _convert_value(value, type_hint)
        else:
            # Unknown key — @_additional_properties decorator will capture it.
            kwargs[key] = value

    return cls(**kwargs)
