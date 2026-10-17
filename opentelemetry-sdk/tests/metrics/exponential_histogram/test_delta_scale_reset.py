# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Regression tests for the DELTA scale reset between collections (#5716).

With DELTA temporality, the exponential histogram aggregation lowered its
scale when an interval's values spanned a wide range but never raised it
again: ``collect`` reset the buckets and the scale but not the exponent
mapping, so every later delta point inherited the lowest scale any earlier
interval needed. Per the spec, when either range holds not more than one
value the scale SHOULD be the maximum.
"""

from opentelemetry.sdk.metrics import Histogram, MeterProvider
from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping.logarithm_mapping import (
    LogarithmMapping,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    InMemoryMetricReader,
)
from opentelemetry.sdk.metrics.view import (
    ExponentialBucketHistogramAggregation,
    View,
)
from opentelemetry.test import TestCase


def _latency_data_points(reader):
    metrics_data = reader.get_metrics_data()
    if metrics_data is None:
        return []
    return [
        point
        for resource_metrics in metrics_data.resource_metrics
        for scope_metrics in resource_metrics.scope_metrics
        for metric in scope_metrics.metrics
        if metric.name == "latency"
        for point in metric.data.data_points
    ]


def _delta_point(reader):
    return _latency_data_points(reader)[0]


def _delta_histogram():
    reader = InMemoryMetricReader(preferred_temporality={Histogram: AggregationTemporality.DELTA})
    provider = MeterProvider(
        metric_readers=[reader],
        views=[
            View(
                instrument_name="latency",
                aggregation=ExponentialBucketHistogramAggregation(),
            )
        ],
    )
    hist = provider.get_meter(__name__).create_histogram("latency")
    return reader, hist


class TestDeltaScaleReset(TestCase):
    def test_delta_scale_resets_between_intervals(self):
        """A single-value interval after a wide one uses the maximum scale."""
        reader, hist = _delta_histogram()

        hist.record(1e-6)
        hist.record(1e6)
        # the wide interval downscales
        self.assertEqual(_delta_point(reader).scale, 2)

        for _ in range(3):
            hist.record(5.0)
            # max scale: one value only
            self.assertEqual(_delta_point(reader).scale, 20)

    def test_delta_scale_still_downscales_for_wide_intervals(self):
        """Downscaling must keep working for every wide interval."""
        reader, hist = _delta_histogram()

        for _ in range(3):
            hist.record(1e-6)
            hist.record(1e6)
            self.assertEqual(_delta_point(reader).scale, 2)

    def test_scale_reset_survives_empty_interval(self):
        """An interval without records must not consume the reset."""
        reader, hist = _delta_histogram()

        hist.record(1e-6)
        hist.record(1e6)
        self.assertEqual(_delta_point(reader).scale, 2)

        # an interval with no records produces no point
        self.assertEqual(_latency_data_points(reader), [])

        # the next interval still starts from the maximum scale
        hist.record(5.0)
        self.assertEqual(_delta_point(reader).scale, 20)

    def test_scale_resets_on_every_collection(self):
        """The mapping is reset on every collection, not only the first one."""
        reader, hist = _delta_histogram()

        for _ in range(3):
            hist.record(1e-6)
            hist.record(1e6)
            self.assertEqual(_delta_point(reader).scale, 2)

            hist.record(5.0)
            self.assertEqual(_delta_point(reader).scale, 20)

    def test_reset_mapping_buckets_at_max_scale(self):
        """After the reset, values are bucketed with the maximum-scale mapping."""
        reader, hist = _delta_histogram()

        hist.record(1e-6)
        hist.record(1e6)
        self.assertEqual(_delta_point(reader).scale, 2)

        hist.record(5.0)
        point = _delta_point(reader)
        self.assertEqual(point.scale, 20)
        # the bucket index comes from the scale-20 mapping, not from the
        # scale-2 mapping the previous interval downscaled to
        self.assertEqual(point.positive.offset, LogarithmMapping(20).map_to_index(5.0))
        self.assertEqual(tuple(point.positive.bucket_counts), (1,))
