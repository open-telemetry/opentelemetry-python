# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

ExporterT = TypeVar("ExporterT")

CUSTOM_HEADERS: dict[str, str] = {
    "x-custom-header": "custom-value",
    "x-another-header": "another-value",
}


@dataclass
class ExporterConfig(Generic[ExporterT]):
    id: str
    exporter_class: type[ExporterT]
    kwargs: dict[str, Any] = field(default_factory=dict)
    lazy_kwargs: dict[str, Callable[[], Any]] = field(default_factory=dict)

    def build(self) -> ExporterT:
        kwargs = {
            **self.kwargs,
            **{key: factory() for key, factory in self.lazy_kwargs.items()},
        }
        return self.exporter_class(**kwargs)


def _attrs_to_dict(attributes) -> dict:
    result = {}
    for kv in attributes:
        which = kv.value.WhichOneof("value")
        if which == "string_value":
            result[kv.key] = kv.value.string_value
        elif which == "int_value":
            result[kv.key] = kv.value.int_value
        elif which == "double_value":
            result[kv.key] = kv.value.double_value
        elif which == "bool_value":
            result[kv.key] = kv.value.bool_value
    return result
