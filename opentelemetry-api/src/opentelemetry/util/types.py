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
