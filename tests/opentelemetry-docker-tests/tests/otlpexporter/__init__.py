# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

ExporterT = TypeVar("ExporterT")


@dataclass
class ExporterConfig(Generic[ExporterT]):
    id: str
    exporter_class: type[ExporterT]
    kwargs: dict[str, Any] = field(default_factory=dict)

    def build(self) -> ExporterT:
        return self.exporter_class(**self.kwargs)


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
