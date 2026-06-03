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
from typing import Any, TypeVar, Union, get_args, get_origin

_T = TypeVar("_T")


def _unwrap_optional(type_hint: Any) -> Any:
    """Strip ``None`` from a ``X | None`` / ``Optional[X]`` annotation.

    Returns the unwrapped type, or the original hint if not a Union with None.
    """
    origin = get_origin(type_hint)
    if origin is Union or origin is types.UnionType:
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


def _resolve_type_hints(cls: type) -> dict[str, Any]:
    # Wrapped so callers see ``dict[str, Any]`` rather than the typing internals;
    # this keeps astroid from importing Python 3.14's ``annotationlib`` (which
    # uses t-strings) during inference under pylint 3.x. See pull/5269 history.
    resolved: dict[str, Any] = {}
    resolved.update(typing.get_type_hints(cls, include_extras=False))
    return resolved


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

    hints = _resolve_type_hints(cls)
    known_fields = {f.name for f in dataclasses.fields(cls)}
    kwargs: dict[str, Any] = {}

    for key, value in data.items():
        if key in known_fields:
            type_hint = hints.get(key)
            kwargs[key] = _convert_value(value, type_hint)
        else:
            # Unknown key — @_additional_properties decorator will capture it.
            kwargs[key] = value

    return cls(**kwargs)
