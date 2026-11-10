# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from enum import Enum
from typing import Final

from typing_extensions import deprecated

OPENTRACING_REF_TYPE: Final = "opentracing.ref_type"
"""
Deprecated: OpenTracing compatibility requirements are [deprecated in OpenTelemetry Specification](https://opentelemetry.io/docs/specs/otel/compatibility/opentracing/).
"""


@deprecated(
    "The attribute opentracing.ref_type is deprecated - OpenTracing compatibility requirements are [deprecated in OpenTelemetry Specification](https://opentelemetry.io/docs/specs/otel/compatibility/opentracing/)"
)
class OpentracingRefTypeValues(Enum):
    CHILD_OF = "child_of"
    """The parent Span depends on the child Span in some capacity."""
    FOLLOWS_FROM = "follows_from"
    """The parent Span doesn't depend in any way on the result of the child Span."""
