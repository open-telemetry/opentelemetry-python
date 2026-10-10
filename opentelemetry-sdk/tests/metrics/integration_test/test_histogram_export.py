# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase

from opentelemetry.sdk.metrics import Histogram, MeterProvider
from opentelemetry.sdk.metrics._internal.exemplar import (
    AlwaysOffExemplarFilter,
    AlwaysOnExemplarFilter,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    InMemoryMetricReader,
)
from opentelemetry.sdk.metrics.view import (
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
    View,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource


class TestHistogramExport(TestCase):
    def test_histogram_collection_without_min_max(self):
        for aggregation_type in ExplicitBucketHistogramAggregation, ExponentialBucketHistogramAggregation:
            for temporality in AggregationTemporality.DELTA, AggregationTemporality.CUMULATIVE:
                with self.subTest(aggregation=aggregation_type.__name__, temporality=temporality):
                    reader = InMemoryMetricReader(preferred_temporality={Histogram: temporality})
                    provider = MeterProvider(
                        metric_readers=[reader],
                        views=[
                            View(
                                instrument_name="my_histogram",
                                aggregation=aggregation_type(record_min_max=False),
                            )
                        ],
                    )
                    try:
                        histogram = provider.get_meter("my-meter").create_histogram("my_histogram")
                        second_count, second_sum = (1, 20) if temporality == AggregationTemporality.DELTA else (3, 75)
                        for values, expected_count, expected_sum in (
                            ((5, 50), 2, 55),
                            ((20,), second_count, second_sum),
                        ):
                            for value in values:
                                histogram.record(value)
                            metrics_data = reader.get_metrics_data()
                            self.assertIsNotNone(metrics_data)
                            metric = next(
                                metric
                                for resource_metrics in metrics_data.resource_metrics
                                for scope_metrics in resource_metrics.scope_metrics
                                for metric in scope_metrics.metrics
                                if metric.name == "my_histogram"
                            )
                            self.assertEqual(metric.data.aggregation_temporality, temporality)
                            self.assertEqual(len(metric.data.data_points), 1)
                            point = metric.data.data_points[0]
                            self.assertIsNone(point.min)
                            self.assertIsNone(point.max)
                            self.assertEqual(point.count, expected_count)
                            self.assertEqual(point.sum, expected_sum)
                    finally:
                        provider.shutdown()

    def test_histogram_counter_collection(self):
        in_memory_metric_reader = InMemoryMetricReader()

        provider = MeterProvider(
            resource=Resource.create({SERVICE_NAME: "otel-test"}),
            metric_readers=[in_memory_metric_reader],
        )

        meter = provider.get_meter("my-meter")

        histogram = meter.create_histogram("my_histogram")
        counter = meter.create_counter("my_counter")
        histogram.record(5, {"attribute": "value"})
        counter.add(1, {"attribute": "value_counter"})

        metric_data = in_memory_metric_reader.get_metrics_data()

        self.assertEqual(len(metric_data.resource_metrics[0].scope_metrics[0].metrics), 2)

        self.assertEqual(
            (metric_data.resource_metrics[0].scope_metrics[0].metrics[0].data.data_points[0].bucket_counts),
            (0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        )
        self.assertEqual(
            (metric_data.resource_metrics[0].scope_metrics[0].metrics[1].data.data_points[0].value),
            1,
        )

        metric_data = in_memory_metric_reader.get_metrics_data()

        self.assertEqual(len(metric_data.resource_metrics[0].scope_metrics[0].metrics), 2)
        self.assertEqual(
            (metric_data.resource_metrics[0].scope_metrics[0].metrics[0].data.data_points[0].bucket_counts),
            (0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        )
        self.assertEqual(
            (metric_data.resource_metrics[0].scope_metrics[0].metrics[1].data.data_points[0].value),
            1,
        )

    def test_histogram_with_exemplars(self):
        in_memory_metric_reader = InMemoryMetricReader()

        provider = MeterProvider(
            resource=Resource.create({SERVICE_NAME: "otel-test"}),
            metric_readers=[in_memory_metric_reader],
            exemplar_filter=AlwaysOnExemplarFilter(),
        )
        meter = provider.get_meter("my-meter")
        histogram = meter.create_histogram("my_histogram")

        histogram.record(2, {"attribute": "value1"})  # Should go in the first bucket
        histogram.record(7, {"attribute": "value2"})  # Should go in the second bucket
        histogram.record(9, {"attribute": "value2"})  # Should also go in the second bucket
        histogram.record(15, {"attribute": "value3"})  # Should go in the third bucket

        metric_data = in_memory_metric_reader.get_metrics_data()

        self.assertEqual(len(metric_data.resource_metrics[0].scope_metrics[0].metrics), 1)
        histogram_metric = metric_data.resource_metrics[0].scope_metrics[0].metrics[0]

        self.assertEqual(len(histogram_metric.data.data_points), 3)

        self.assertEqual(len(histogram_metric.data.data_points[0].exemplars), 1)
        self.assertEqual(len(histogram_metric.data.data_points[1].exemplars), 1)
        self.assertEqual(len(histogram_metric.data.data_points[2].exemplars), 1)

        self.assertEqual(histogram_metric.data.data_points[0].sum, 2)
        self.assertEqual(histogram_metric.data.data_points[1].sum, 16)
        self.assertEqual(histogram_metric.data.data_points[2].sum, 15)

        self.assertEqual(histogram_metric.data.data_points[0].exemplars[0].value, 2.0)
        self.assertEqual(histogram_metric.data.data_points[1].exemplars[0].value, 9.0)
        self.assertEqual(histogram_metric.data.data_points[2].exemplars[0].value, 15.0)

    def test_filter_with_exemplars(self):
        in_memory_metric_reader = InMemoryMetricReader()

        provider = MeterProvider(
            resource=Resource.create({SERVICE_NAME: "otel-test"}),
            metric_readers=[in_memory_metric_reader],
            exemplar_filter=AlwaysOffExemplarFilter(),
        )
        meter = provider.get_meter("my-meter")
        histogram = meter.create_histogram("my_histogram")

        histogram.record(2, {"attribute": "value1"})  # Should go in the first bucket
        histogram.record(7, {"attribute": "value2"})  # Should go in the second bucket

        metric_data = in_memory_metric_reader.get_metrics_data()

        self.assertEqual(len(metric_data.resource_metrics[0].scope_metrics[0].metrics), 1)
        histogram_metric = metric_data.resource_metrics[0].scope_metrics[0].metrics[0]

        self.assertEqual(len(histogram_metric.data.data_points), 2)

        self.assertEqual(len(histogram_metric.data.data_points[0].exemplars), 0)
        self.assertEqual(len(histogram_metric.data.data_points[1].exemplars), 0)
