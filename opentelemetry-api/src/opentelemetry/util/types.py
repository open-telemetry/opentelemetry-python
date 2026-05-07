# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from typing import Mapping, Optional, Sequence, Tuple, Union

# This is the implementation of the "Any" type as specified by the specifications of OpenTelemetry data model for logs.
# For more details, refer to the OTel specification:
# https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/logs/data-model.md#type-any
AnyValue = Union[
    str,
    bool,
    int,
    float,
    bytes,
    Sequence["AnyValue"],
    Mapping[str, "AnyValue"],
    None,
]

AttributeValue = Union[
    str,
    bool,
    int,
    float,
    Sequence[str],
    Sequence[bool],
    Sequence[int],
    Sequence[float],
]
Attributes = Optional[Mapping[str, AttributeValue]]
AttributesAsKey = Tuple[
    Tuple[
        str,
        Union[
            str,
            bool,
            int,
            float,
            Tuple[Optional[str], ...],
            Tuple[Optional[bool], ...],
            Tuple[Optional[int], ...],
            Tuple[Optional[float], ...],
        ],
    ],
    ...,
]

_ExtendedAttributes = Mapping[str, "AnyValue"]
