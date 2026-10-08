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
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    InMemoryMetricReader,
)
from opentelemetry.sdk.metrics.view import (
    ExponentialBucketHistogramAggregation,
    View,
)
from opentelemetry.test import TestCase


def _delta_point(reader):
    return reader.get_metrics_data().resource_metrics[0].scope_metrics[0].metrics[0].data.data_points[0]


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
