# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from typing import TypedDict

    class _NoExtraKwargs(TypedDict):  # noqa: PYI049  # used by other modules
        """Accepts no keyword arguments.

        Annotate an implementation's ``**_kwargs: Unpack[_NoExtraKwargs]`` so the
        method accepts and ignores unknown keyword arguments at runtime (keeping
        it forward compatible), while type checkers reject any extra keyword
        argument.
        """


# This is the implementation of the "Any" type as specified by the specifications of OpenTelemetry data model for logs.
# For more details, refer to the OTel specification:
# https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/logs/data-model.md#type-any
AnyValue: TypeAlias = str | bool | int | float | bytes | Sequence["AnyValue"] | Mapping[str, "AnyValue"] | None
AttributeValue: TypeAlias = AnyValue
Attributes = Mapping[str, AnyValue] | None

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
