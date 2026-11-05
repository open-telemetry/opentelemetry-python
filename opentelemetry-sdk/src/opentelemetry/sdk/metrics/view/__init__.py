# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""View and aggregation configuration for the metrics SDK.

This package re-exports ``View``, which selects instruments and customizes the
metric streams they feed, together with the aggregations a view can be given:
the ``Aggregation`` base class and its subclasses ``DefaultAggregation``,
``DropAggregation``, ``ExplicitBucketHistogramAggregation``,
``ExponentialBucketHistogramAggregation``, ``LastValueAggregation`` and
``SumAggregation``.

``View`` is implemented in ``opentelemetry.sdk.metrics._internal.view`` and the
aggregations in ``opentelemetry.sdk.metrics._internal.aggregation``. Import
them from this package rather than from the ``_internal`` package, whose
layout carries no stability guarantee.
"""

from opentelemetry.sdk.metrics._internal.aggregation import (
    Aggregation,
    DefaultAggregation,
    DropAggregation,
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
    LastValueAggregation,
    SumAggregation,
)
from opentelemetry.sdk.metrics._internal.view import View

__all__ = [
    "Aggregation",
    "DefaultAggregation",
    "DropAggregation",
    "ExplicitBucketHistogramAggregation",
    "ExponentialBucketHistogramAggregation",
    "LastValueAggregation",
    "SumAggregation",
    "View",
]
