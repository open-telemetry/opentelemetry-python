# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Recursive dict-to-dataclass conversion for parsed config data.

The YAML/JSON loader produces nested dicts. Factory functions expect typed
dataclass instances (e.g. ``TracerProvider``, ``SpanProcessor``). This module
walks each field's type annotation and converts nested dicts into their
corresponding dataclass types.
"""

from __future__ import annotations

import dataclasses
import enum
import types
import typing
from collections.abc import Mapping
from typing import Any, TypeVar, get_args, get_origin

_T = TypeVar("_T")


def _unwrap_optional(type_hint: Any) -> Any:
    """Strip ``None`` from a ``X | None`` / ``Optional[X]`` annotation.

    Returns the unwrapped type, or the original hint if not a union with None.
    """
    origin = get_origin(type_hint)
    if origin is types.UnionType or origin is typing.Union:
        non_none = [t for t in get_args(type_hint) if t is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return type_hint


def _convert_value(value: Any, type_hint: Any) -> Any:
    """Convert a value according to its type hint.

    Recursively converts dicts to dataclasses and lists of dicts to lists of
    dataclasses. Other values (primitives, enums, ``dict[str, Any]`` aliases)
    pass through unchanged.
    """
    if value is None:
        return None

    unwrapped = _unwrap_optional(type_hint)
    origin = get_origin(unwrapped)

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
        and dataclasses.is_dataclass(unwrapped)
        and isinstance(value, dict)
    ):
        return _dict_to_dataclass(value, unwrapped)

    # Enum type — coerce string/value to the Enum member
    if (
        isinstance(unwrapped, type)
        and issubclass(unwrapped, enum.Enum)
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
    if not dataclasses.is_dataclass(cls):
        raise TypeError(f"{cls.__name__} is not a dataclass")

    # Annotated as ``dict[str, Any]`` so astroid stops tracing into
    # ``typing.get_type_hints`` — under pylint 3.x that path leads into
    # Python 3.14's ``annotationlib`` (which uses t-strings) and crashes.
    hints: dict[str, Any] = dict(
        typing.get_type_hints(cls, include_extras=False)
    )
    known_fields = {f.name for f in dataclasses.fields(cls)}
    kwargs: dict[str, Any] = {}

    for key, value in data.items():
        # Schema keys like "otlp_file/development" use "/" as a namespace
        # separator; Python field names use "_".  Normalise before lookup.
        field_key = key.replace("/", "_")
        if field_key in known_fields:
            type_hint = hints.get(field_key)
            kwargs[field_key] = _convert_value(value, type_hint)
        else:
            # Unknown key — @_additional_properties decorator will capture it.
            kwargs[key] = value

    return cls(**kwargs)
