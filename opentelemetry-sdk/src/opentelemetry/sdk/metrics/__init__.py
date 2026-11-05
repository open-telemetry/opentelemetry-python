# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Entry point of the metrics SDK.

This package re-exports the names that make up the public metrics SDK:
``MeterProvider`` and ``Meter``; the instrument classes ``Counter``,
``UpDownCounter``, ``Histogram``, ``ObservableCounter``,
``ObservableUpDownCounter``, ``ObservableGauge`` and ``_Gauge``; the exemplar
filters ``ExemplarFilter``, ``AlwaysOnExemplarFilter``,
``AlwaysOffExemplarFilter`` and ``TraceBasedExemplarFilter``; the exemplar
types ``Exemplar``, ``ExemplarReservoir``,
``SimpleFixedSizeExemplarReservoir`` and
``AlignedHistogramBucketExemplarReservoir``; and ``MetricsTimeoutError``. The
``export`` and ``view`` subpackages are imported here as well, so that
``opentelemetry.sdk.metrics.export`` and ``opentelemetry.sdk.metrics.view``
resolve after importing this package alone.

Every one of those names is implemented under
``opentelemetry.sdk.metrics._internal``. Import them from this package rather
than from the ``_internal`` package, whose layout carries no stability
guarantee.
"""

from opentelemetry.sdk.metrics import export, view
from opentelemetry.sdk.metrics._internal import Meter, MeterProvider
from opentelemetry.sdk.metrics._internal.exceptions import MetricsTimeoutError
from opentelemetry.sdk.metrics._internal.exemplar import (
    AlignedHistogramBucketExemplarReservoir,
    AlwaysOffExemplarFilter,
    AlwaysOnExemplarFilter,
    Exemplar,
    ExemplarFilter,
    ExemplarReservoir,
    SimpleFixedSizeExemplarReservoir,
    TraceBasedExemplarFilter,
)
from opentelemetry.sdk.metrics._internal.instrument import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics._internal.instrument import Gauge as _Gauge

__all__ = [
    "AlignedHistogramBucketExemplarReservoir",
    "AlwaysOffExemplarFilter",
    "AlwaysOnExemplarFilter",
    "Counter",
    "Exemplar",
    "ExemplarFilter",
    "ExemplarReservoir",
    "Histogram",
    "Meter",
    "MeterProvider",
    "MetricsTimeoutError",
    "ObservableCounter",
    "ObservableGauge",
    "ObservableUpDownCounter",
    "SimpleFixedSizeExemplarReservoir",
    "TraceBasedExemplarFilter",
    "UpDownCounter",
    "_Gauge",
    "export",
    "view",
]
