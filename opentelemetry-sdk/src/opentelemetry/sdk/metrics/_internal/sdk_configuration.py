# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The bundle of meter provider settings shared with every metric reader.

``MeterProvider`` builds a single ``SdkConfiguration`` at construction time and
hands the same instance to every ``MetricReaderStorage``, so the readers all
see the same resource, the same views and the same exemplar filter.
"""

# pylint: disable=unused-import

from collections.abc import Sequence
from dataclasses import dataclass

# This kind of import is needed to avoid Sphinx errors.
import opentelemetry.sdk.metrics
import opentelemetry.sdk.resources


@dataclass
class SdkConfiguration:
    """Settings a ``MeterProvider`` passes down to its metric readers.

    Args:
        exemplar_filter: Decides which measurements may become exemplars. It
            is consulted once per recorded measurement, before the value
            reaches the exemplar reservoir.
        resource: The resource that every metric produced by this meter
            provider is attributed to.
        views: The views registered on the meter provider, in registration
            order. A single instrument may match several of them, in which
            case it produces one stream per match. An empty sequence means
            every instrument keeps its default aggregation.
    """

    exemplar_filter: "opentelemetry.sdk.metrics.ExemplarFilter"
    resource: "opentelemetry.sdk.resources.Resource"
    views: Sequence["opentelemetry.sdk.metrics.view.View"]
