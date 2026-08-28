# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""OTLP encoding of histogram min/max when record_min_max is disabled.

The SDK reports None for both; protobuf must then leave the optional fields
unset rather than emitting the +Inf/-Inf sentinels.
"""

import unittest

from opentelemetry.exporter.otlp.proto.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.metrics.view import (
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
    View,
)


def _encoded_point(aggregation):
    reader = InMemoryMetricReader()
    provider = MeterProvider(
        metric_readers=[reader],
        views=[View(instrument_name="hist", aggregation=aggregation)],
    )
    provider.get_meter(__name__).create_histogram("hist").record(5)
    data = reader.get_metrics_data()
    metric = encode_metrics(data).resource_metrics[0].scope_metrics[0].metrics[0]
    point = getattr(metric, metric.WhichOneof("data")).data_points[0]
    provider.shutdown()
    return point


class TestHistogramMinMaxEncoding(unittest.TestCase):
    AGGREGATIONS = {
        "explicit": ExplicitBucketHistogramAggregation,
        "exponential": ExponentialBucketHistogramAggregation,
    }

    def test_fields_absent_when_recording_disabled(self):
        for name, aggregation in self.AGGREGATIONS.items():
            with self.subTest(aggregation=name):
                point = _encoded_point(aggregation(record_min_max=False))
                self.assertFalse(point.HasField("min"))
                self.assertFalse(point.HasField("max"))

    def test_fields_present_when_recording_enabled(self):
        for name, aggregation in self.AGGREGATIONS.items():
            with self.subTest(aggregation=name):
                point = _encoded_point(aggregation(record_min_max=True))
                self.assertTrue(point.HasField("min"))
                self.assertTrue(point.HasField("max"))
                self.assertEqual(point.min, 5)
