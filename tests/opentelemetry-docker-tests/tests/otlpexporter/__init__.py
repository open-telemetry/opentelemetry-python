# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, TypeVar
from uuid import uuid4

ExporterT = TypeVar("ExporterT")

CUSTOM_HEADERS: dict[str, str] = {
    "x-custom-header": "custom-value",
    "x-another-header": "another-value",
}

# Directory bind-mounted into the collector container (see docker-compose.yml).
# Resolved relative to the compose file, which sits one level above this package.
OTLP_FILE_DATA_DIR = Path(__file__).parent.parent / "otlp-file-data"


@dataclass
class ExporterConfig(Generic[ExporterT]):
    id: str
    exporter_class: type[ExporterT]
    kwargs: dict[str, Any] = field(default_factory=dict)
    lazy_kwargs: Callable[[], dict[str, Any]] | None = None

    def build(self) -> ExporterT:
        extra = self.lazy_kwargs() if self.lazy_kwargs is not None else {}
        return self.exporter_class(**self.kwargs, **extra)


def new_otlp_file(signal: str) -> str:
    """Return a unique .jsonl path under the collector-mounted directory.

    ``signal`` is one of ``"traces"``, ``"metrics"``, ``"logs"`` and selects the
    subdirectory the collector's ``otlp_json_file/<signal>`` receiver tails.
    """
    directory = OTLP_FILE_DATA_DIR / signal
    directory.mkdir(parents=True, exist_ok=True)
    return str(directory / f"{uuid4().hex}.jsonl")


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
