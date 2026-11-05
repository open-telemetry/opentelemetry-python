# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The metrics a metric reader emits about its own collections.

One instrument is created here, the histogram named
``otel.sdk.metric_reader.collection.duration``, declared in
``opentelemetry.semconv._incubating.metrics.otel_metrics`` and recorded in
seconds. Every recording carries ``otel.component.type``, the kind of reader,
and ``otel.component.name``, that kind followed by a slash and the number of
``MetricReaderMetrics`` objects of that kind built before this one. One reader
builds two of them, one in ``MetricReader.__init__`` and one when it is
registered on a ``MeterProvider``, and only the second ever records anything,
so a lone periodic reader emits ``periodic_metric_reader/1``.

``MetricReader`` holds one of these objects and calls ``record_collection``
once per collection. The object is a ``NoOpMetricReaderMetrics`` unless
``OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED`` is set to ``true``, which keeps
the SDK from measuring itself by default.
"""

from collections import Counter
from typing import Protocol

from opentelemetry.metrics import MeterProvider
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OTEL_COMPONENT_NAME,
    OTEL_COMPONENT_TYPE,
)
from opentelemetry.semconv._incubating.metrics.otel_metrics import (
    create_otel_sdk_metric_reader_collection_duration,
)

_component_counter = Counter()


class MetricReaderMetricsT(Protocol):
    """What a metric reader expects of the object it reports collections to.

    Both ``MetricReaderMetrics`` and ``NoOpMetricReaderMetrics`` satisfy this
    protocol, which lets a reader hold either one without testing which.
    """

    def record_collection(self, duration: float) -> None:
        """Report that one collection took ``duration``.

        Args:
            duration: How long the collection took, in seconds.
        """


class NoOpMetricReaderMetrics:
    """The stand-in used while the SDK's own metrics are switched off.

    Every recording is discarded, so no instrument is created and no meter is
    requested from the meter provider.
    """

    def record_collection(self, duration: float) -> None:
        """Discard the recording.

        Args:
            duration: How long the collection took, in seconds. Unused.
        """


class MetricReaderMetrics:
    """Records the duration of each collection of one metric reader.

    The instance number that goes into ``otel.component.name`` is taken from a
    module-level counter keyed by component type, which is never reset, so
    building and discarding readers over the life of the process keeps raising
    the number rather than reusing a freed one.

    Args:
        component_type: The value of ``otel.component.type`` for this reader,
            either a value from the semantic conventions such as
            ``periodic_metric_reader`` or the qualified name of the reader
            class when the reader declares none.
        meter_provider: The provider the histogram is created on. Passing a
            ``NoOpMeterProvider`` yields a meter whose instruments discard
            everything, which is what a reader holds until it is registered on
            a real ``MeterProvider``.
    """

    def __init__(self, component_type: str, meter_provider: MeterProvider) -> None:
        """Build the instance and create the histogram.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        meter = meter_provider.get_meter("opentelemetry-sdk")

        count = _component_counter[component_type]
        _component_counter[component_type] = count + 1

        self._standard_attrs = {
            OTEL_COMPONENT_TYPE: component_type,
            OTEL_COMPONENT_NAME: f"{component_type}/{count}",
        }

        self._collection_duration = create_otel_sdk_metric_reader_collection_duration(meter)

    def record_collection(self, duration: float) -> None:
        """Record one collection on the histogram.

        The caller times the collection whether it succeeded or failed, and
        no ``error.type`` attribute is added here, so a failed collection is
        recorded under the same attributes as a successful one.

        Args:
            duration: How long the collection took, in seconds.
        """
        self._collection_duration.record(duration, self._standard_attrs)


def create_metric_reader_metrics(
    component_type: str,
    meter_provider: MeterProvider,
    enabled: bool,
) -> MetricReaderMetricsT:
    """Build the object a metric reader reports its collections to.

    Args:
        component_type: The value of ``otel.component.type`` for the reader.
            Ignored when ``enabled`` is false.
        meter_provider: The provider the histogram is created on. Ignored when
            ``enabled`` is false, so no meter is requested in that case.
        enabled: Whether the SDK emits metrics about itself, read from
            ``OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED`` by the caller.

    Returns:
        A ``MetricReaderMetrics`` when ``enabled`` is true, otherwise a
        ``NoOpMetricReaderMetrics``. The call also consumes the next instance
        number for ``component_type`` when ``enabled`` is true, and consumes
        none when it is false.
    """
    if not enabled:
        return NoOpMetricReaderMetrics()

    return MetricReaderMetrics(component_type, meter_provider)
