# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""With record_min_max disabled the min/max fields must be absent, not sentinels.

The aggregators seed min/max with +inf/-inf. If those sentinels reach a data
point they are exported as present OTLP fields, producing a histogram whose
minimum is +Infinity and maximum is -Infinity, and `to_json` emits the literals
`Infinity` / `-Infinity`, which are not valid JSON.
"""

import json
import unittest

from opentelemetry.exporter.otlp.proto.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.sdk.metrics import Histogram as HistogramInstrument
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    InMemoryMetricReader,
)
from opentelemetry.sdk.metrics.view import (
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
    View,
)


def _reject_non_json_constants(constant):
    raise ValueError(f"{constant!r} is not valid JSON")


class _HistogramCase:
    """Drive one histogram aggregation through a reader."""

    def __init__(self, aggregation, temporality=AggregationTemporality.CUMULATIVE):
        self.reader = InMemoryMetricReader(
            preferred_temporality={HistogramInstrument: temporality},
        )
        self.provider = MeterProvider(
            metric_readers=[self.reader],
            views=[View(instrument_name="hist", aggregation=aggregation)],
        )
        self.histogram = self.provider.get_meter(__name__).create_histogram("hist")

    def collect(self):
        data = self.reader.get_metrics_data()
        return data.resource_metrics[0].scope_metrics[0].metrics[0].data.data_points[0]

    def collect_encoded(self):
        data = self.reader.get_metrics_data()
        metric = encode_metrics(data).resource_metrics[0].scope_metrics[0].metrics[0]
        return getattr(metric, metric.WhichOneof("data")).data_points[0]

    def shutdown(self):
        self.provider.shutdown()


class TestRecordMinMaxDisabled(unittest.TestCase):
    AGGREGATIONS = {
        "explicit": ExplicitBucketHistogramAggregation,
        "exponential": ExponentialBucketHistogramAggregation,
    }

    def test_data_point_leaves_min_and_max_unset(self):
        for name, aggregation in self.AGGREGATIONS.items():
            with self.subTest(aggregation=name):
                case = _HistogramCase(aggregation(record_min_max=False))
                case.histogram.record(5)
                case.histogram.record(50)
                point = case.collect()
                self.assertIsNone(point.min)
                self.assertIsNone(point.max)
                self.assertEqual(point.sum, 55)
                self.assertEqual(point.count, 2)
                case.shutdown()

    def test_otlp_fields_are_absent(self):
        for name, aggregation in self.AGGREGATIONS.items():
            with self.subTest(aggregation=name):
                case = _HistogramCase(aggregation(record_min_max=False))
                case.histogram.record(5)
                point = case.collect_encoded()
                self.assertFalse(point.HasField("min"))
                self.assertFalse(point.HasField("max"))
                case.shutdown()

    def test_to_json_is_valid_json(self):
        for name, aggregation in self.AGGREGATIONS.items():
            with self.subTest(aggregation=name):
                case = _HistogramCase(aggregation(record_min_max=False))
                case.histogram.record(5)
                payload = case.collect().to_json()
                json.loads(payload, parse_constant=_reject_non_json_constants)
                case.shutdown()

    def test_cumulative_collections_stay_unset(self):
        """The delta-to-cumulative merge must not resurrect the sentinels."""
        for name, aggregation in self.AGGREGATIONS.items():
            with self.subTest(aggregation=name):
                case = _HistogramCase(aggregation(record_min_max=False))
                case.histogram.record(5)
                case.collect()
                case.histogram.record(50)
                point = case.collect()
                self.assertIsNone(point.min)
                self.assertIsNone(point.max)
                self.assertEqual(point.sum, 55)
                case.shutdown()

    def test_delta_temporality_leaves_min_and_max_unset(self):
        case = _HistogramCase(
            ExplicitBucketHistogramAggregation(record_min_max=False),
            temporality=AggregationTemporality.DELTA,
        )
        case.histogram.record(5)
        point = case.collect()
        self.assertIsNone(point.min)
        self.assertIsNone(point.max)
        case.shutdown()


class TestRecordMinMaxEnabled(unittest.TestCase):
    """The default must keep working exactly as before."""

    AGGREGATIONS = {
        "explicit": ExplicitBucketHistogramAggregation,
        "exponential": ExponentialBucketHistogramAggregation,
    }

    def test_min_and_max_are_recorded(self):
        for name, aggregation in self.AGGREGATIONS.items():
            with self.subTest(aggregation=name):
                case = _HistogramCase(aggregation(record_min_max=True))
                case.histogram.record(5)
                case.histogram.record(50)
                point = case.collect()
                self.assertEqual(point.min, 5)
                self.assertEqual(point.max, 50)
                case.shutdown()

    def test_cumulative_min_and_max_span_collections(self):
        for name, aggregation in self.AGGREGATIONS.items():
            with self.subTest(aggregation=name):
                case = _HistogramCase(aggregation(record_min_max=True))
                case.histogram.record(50)
                case.collect()
                case.histogram.record(5)
                point = case.collect()
                self.assertEqual(point.min, 5)
                self.assertEqual(point.max, 50)
                case.shutdown()

    def test_otlp_fields_are_present(self):
        case = _HistogramCase(ExplicitBucketHistogramAggregation(record_min_max=True))
        case.histogram.record(5)
        point = case.collect_encoded()
        self.assertTrue(point.HasField("min"))
        self.assertTrue(point.HasField("max"))
        self.assertEqual(point.min, 5)
        case.shutdown()
