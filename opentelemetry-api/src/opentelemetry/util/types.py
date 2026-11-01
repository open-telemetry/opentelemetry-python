# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Type aliases for the attribute and log body values the API accepts.

The aliases here spell out which Python values are valid wherever the API takes
attributes or a log record body. :data:`AnyValue` is the recursive alias
matching the ``any`` type of the OpenTelemetry log data model, and
:data:`Attributes` is the mapping form accepted by spans, metrics and logs.
"""

from collections.abc import Mapping, Sequence
from typing import TypeAlias

# This is the implementation of the "Any" type as specified by the specifications of OpenTelemetry data model for logs.
# For more details, refer to the OTel specification:
# https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/logs/data-model.md#type-any
AnyValue: TypeAlias = str | bool | int | float | bytes | Sequence["AnyValue"] | Mapping[str, "AnyValue"] | None
"""Any value the OpenTelemetry log data model accepts.

The alias is recursive: a value is a scalar, ``None``, a sequence of
:data:`AnyValue`, or a mapping from :class:`str` to :data:`AnyValue`.
"""

AttributeValue: TypeAlias = AnyValue
"""The value half of a single attribute.

This is an alias of :data:`AnyValue`, kept as a separate name so that code
annotating attributes reads as such.
"""

Attributes = Mapping[str, AnyValue] | None
"""A full set of attributes, or ``None`` when no attribute is supplied.

Keys are non-empty strings. ``None`` and an empty mapping are both accepted
wherever the API takes attributes, and both mean that no attribute is set.
"""

# Deprecated type, do not use.
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
"""A set of attributes flattened into a hashable tuple of name/value pairs.

.. deprecated:: 1.45.0
    This alias is retained for backwards compatibility and is not used by the
    API. Use :data:`Attributes` instead.
"""
