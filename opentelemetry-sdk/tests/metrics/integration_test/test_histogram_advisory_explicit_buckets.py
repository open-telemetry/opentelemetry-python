# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.aggregation import (
    _DEFAULT_EXPLICIT_BUCKET_HISTOGRAM_AGGREGATION_BOUNDARIES,
)
from opentelemetry.sdk.metrics._internal.instrument import Histogram
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.metrics.view import (
    ExplicitBucketHistogramAggregation,
    View,
)
from opentelemetry.semconv._incubating.metrics.http_metrics import (
    create_http_client_request_duration,
    create_http_server_request_duration,
)


class TestHistogramAdvisory(TestCase):
    def test_http_request_duration_buckets(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(metric_readers=[reader])
        self.addCleanup(meter_provider.shutdown)
        meter = meter_provider.get_meter("testmeter")
        for create_histogram in (
            create_http_client_request_duration,
            create_http_server_request_duration,
        ):
            histogram = create_histogram(meter)
            for duration in (0.004, 0.06, 0.7):
                histogram.record(duration)

        metrics = reader.get_metrics_data().resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual(
            {metric.name for metric in metrics},
            {"http.client.request.duration", "http.server.request.duration"},
        )
        for metric in metrics:
            with self.subTest(name=metric.name):
                self.assertEqual(metric.unit, "s")
                point = metric.data.data_points[0]
                self.assertEqual(
                    point.explicit_bounds,
                    (0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10),
                )
                self.assertEqual(point.bucket_counts, (1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0))

    def test_default(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
        )
        meter = meter_provider.get_meter("testmeter")
        histogram = meter.create_histogram(
            "testhistogram",
            explicit_bucket_boundaries_advisory=[1.0, 2.0, 3.0],
        )
        histogram.record(1, {"label": "value"})
        histogram.record(2, {"label": "value"})
        histogram.record(3, {"label": "value"})

        metrics = reader.get_metrics_data()
        self.assertEqual(len(metrics.resource_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics[0].metrics), 1)
        metric = metrics.resource_metrics[0].scope_metrics[0].metrics[0]
        self.assertEqual(metric.name, "testhistogram")
        self.assertEqual(metric.data.data_points[0].explicit_bounds, (1.0, 2.0, 3.0))

    def test_empty_buckets(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
        )
        meter = meter_provider.get_meter("testmeter")
        histogram = meter.create_histogram(
            "testhistogram",
            explicit_bucket_boundaries_advisory=[],
        )
        histogram.record(1, {"label": "value"})
        histogram.record(2, {"label": "value"})
        histogram.record(3, {"label": "value"})

        metrics = reader.get_metrics_data()
        self.assertEqual(len(metrics.resource_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics[0].metrics), 1)
        metric = metrics.resource_metrics[0].scope_metrics[0].metrics[0]
        self.assertEqual(metric.name, "testhistogram")
        self.assertEqual(metric.data.data_points[0].explicit_bounds, ())

    def test_view_default_aggregation(self):
        reader = InMemoryMetricReader()
        view = View(instrument_name="testhistogram")
        meter_provider = MeterProvider(
            metric_readers=[reader],
            views=[view],
        )
        meter = meter_provider.get_meter("testmeter")
        histogram = meter.create_histogram(
            "testhistogram",
            explicit_bucket_boundaries_advisory=[1.0, 2.0, 3.0],
        )
        histogram.record(1, {"label": "value"})
        histogram.record(2, {"label": "value"})
        histogram.record(3, {"label": "value"})

        metrics = reader.get_metrics_data()
        self.assertEqual(len(metrics.resource_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics[0].metrics), 1)
        metric = metrics.resource_metrics[0].scope_metrics[0].metrics[0]
        self.assertEqual(metric.name, "testhistogram")
        self.assertEqual(metric.data.data_points[0].explicit_bounds, (1.0, 2.0, 3.0))

    def test_view_overrides_buckets(self):
        reader = InMemoryMetricReader()
        view = View(
            instrument_name="testhistogram",
            aggregation=ExplicitBucketHistogramAggregation(boundaries=[10.0, 100.0, 1000.0]),
        )
        meter_provider = MeterProvider(
            metric_readers=[reader],
            views=[view],
        )
        meter = meter_provider.get_meter("testmeter")
        histogram = meter.create_histogram(
            "testhistogram",
            explicit_bucket_boundaries_advisory=[1.0, 2.0, 3.0],
        )
        histogram.record(1, {"label": "value"})
        histogram.record(2, {"label": "value"})
        histogram.record(3, {"label": "value"})

        metrics = reader.get_metrics_data()
        self.assertEqual(len(metrics.resource_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics[0].metrics), 1)
        metric = metrics.resource_metrics[0].scope_metrics[0].metrics[0]
        self.assertEqual(metric.name, "testhistogram")
        self.assertEqual(metric.data.data_points[0].explicit_bounds, (10.0, 100.0, 1000.0))

    def test_explicit_aggregation(self):
        reader = InMemoryMetricReader(preferred_aggregation={Histogram: ExplicitBucketHistogramAggregation()})
        meter_provider = MeterProvider(
            metric_readers=[reader],
        )
        meter = meter_provider.get_meter("testmeter")
        histogram = meter.create_histogram(
            "testhistogram",
            explicit_bucket_boundaries_advisory=[1.0, 2.0, 3.0],
        )
        histogram.record(1, {"label": "value"})
        histogram.record(2, {"label": "value"})
        histogram.record(3, {"label": "value"})

        metrics = reader.get_metrics_data()
        self.assertEqual(len(metrics.resource_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics[0].metrics), 1)
        metric = metrics.resource_metrics[0].scope_metrics[0].metrics[0]
        self.assertEqual(metric.name, "testhistogram")
        self.assertEqual(metric.data.data_points[0].explicit_bounds, (1.0, 2.0, 3.0))

    def test_explicit_aggregation_multiple_histograms(self):
        reader = InMemoryMetricReader(preferred_aggregation={Histogram: ExplicitBucketHistogramAggregation()})
        meter_provider = MeterProvider(
            metric_readers=[reader],
        )
        meter = meter_provider.get_meter("testmeter")

        histogram1 = meter.create_histogram(
            "testhistogram1",
            explicit_bucket_boundaries_advisory=[1.0, 2.0, 3.0],
        )
        histogram1.record(1, {"label": "value"})
        histogram1.record(2, {"label": "value"})
        histogram1.record(3, {"label": "value"})

        histogram2 = meter.create_histogram(
            "testhistogram2",
            explicit_bucket_boundaries_advisory=[4.0, 5.0, 6.0],
        )
        histogram2.record(4, {"label": "value"})
        histogram2.record(5, {"label": "value"})
        histogram2.record(6, {"label": "value"})

        metrics = reader.get_metrics_data()
        self.assertEqual(len(metrics.resource_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics[0].metrics), 2)
        metric1 = metrics.resource_metrics[0].scope_metrics[0].metrics[0]
        self.assertEqual(metric1.name, "testhistogram1")
        self.assertEqual(metric1.data.data_points[0].explicit_bounds, (1.0, 2.0, 3.0))
        metric2 = metrics.resource_metrics[0].scope_metrics[0].metrics[1]
        self.assertEqual(metric2.name, "testhistogram2")
        self.assertEqual(metric2.data.data_points[0].explicit_bounds, (4.0, 5.0, 6.0))

    def test_explicit_aggregation_default_boundaries(self):
        reader = InMemoryMetricReader(preferred_aggregation={Histogram: ExplicitBucketHistogramAggregation()})
        meter_provider = MeterProvider(
            metric_readers=[reader],
        )
        meter = meter_provider.get_meter("testmeter")

        histogram = meter.create_histogram(
            "testhistogram",
        )
        histogram.record(1, {"label": "value"})
        histogram.record(2, {"label": "value"})
        histogram.record(3, {"label": "value"})

        metrics = reader.get_metrics_data()
        self.assertEqual(len(metrics.resource_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics), 1)
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics[0].metrics), 1)
        metric = metrics.resource_metrics[0].scope_metrics[0].metrics[0]
        self.assertEqual(metric.name, "testhistogram")
        self.assertEqual(
            metric.data.data_points[0].explicit_bounds,
            _DEFAULT_EXPLICIT_BUCKET_HISTOGRAM_AGGREGATION_BOUNDARIES,
        )
