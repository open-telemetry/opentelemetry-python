# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Mapping, Sequence

# This is the implementation of the "Any" type as specified by the specifications of OpenTelemetry data model for logs.
# For more details, refer to the OTel specification:
# https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/logs/data-model.md#type-any
AnyValue = AttributeValue = (
    str
    | bool
    | int
    | float
    | bytes
    | Sequence["AnyValue"]
    | Mapping[str, "AnyValue"]
    | None
)
Attributes = Mapping[str, AnyValue] | None
# Not sure of the purpose of this type.. this is likely to confuse people..
# I see only 1 usage in the repo: https://github.com/open-telemetry/opentelemetry-python/blob/main/opentelemetry-sdk/src/opentelemetry/sdk/util/__init__.pyi#L28
# No usages in contrib.
AttributesAsKey = tuple[
    tuple[
        str,
        str
        | bool
        | int
        | float
        | tuple[str | None, ...]
        | tuple[bool | None, ...]
        | tuple[int | None, ...]
        | tuple[float | None, ...],
    ],
    ...,
]
