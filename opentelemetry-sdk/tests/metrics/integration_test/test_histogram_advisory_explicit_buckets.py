# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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


class TestHistogramAdvisory(TestCase):
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
        self.assertEqual(
            len(metrics.resource_metrics[0].scope_metrics[0].metrics), 1
        )
        metric = metrics.resource_metrics[0].scope_metrics[0].metrics[0]
        self.assertEqual(metric.name, "testhistogram")
        self.assertEqual(
            metric.data.data_points[0].explicit_bounds, (1.0, 2.0, 3.0)
        )

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
        self.assertEqual(
            len(metrics.resource_metrics[0].scope_metrics[0].metrics), 1
        )
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
        self.assertEqual(
            len(metrics.resource_metrics[0].scope_metrics[0].metrics), 1
        )
        metric = metrics.resource_metrics[0].scope_metrics[0].metrics[0]
        self.assertEqual(metric.name, "testhistogram")
        self.assertEqual(
            metric.data.data_points[0].explicit_bounds, (1.0, 2.0, 3.0)
        )

    def test_view_overrides_buckets(self):
        reader = InMemoryMetricReader()
        view = View(
            instrument_name="testhistogram",
            aggregation=ExplicitBucketHistogramAggregation(
                boundaries=[10.0, 100.0, 1000.0]
            ),
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
        self.assertEqual(
            len(metrics.resource_metrics[0].scope_metrics[0].metrics), 1
        )
        metric = metrics.resource_metrics[0].scope_metrics[0].metrics[0]
        self.assertEqual(metric.name, "testhistogram")
        self.assertEqual(
            metric.data.data_points[0].explicit_bounds, (10.0, 100.0, 1000.0)
        )

    def test_explicit_aggregation(self):
        reader = InMemoryMetricReader(
            preferred_aggregation={
                Histogram: ExplicitBucketHistogramAggregation()
            }
        )
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
        self.assertEqual(
            len(metrics.resource_metrics[0].scope_metrics[0].metrics), 1
        )
        metric = metrics.resource_metrics[0].scope_metrics[0].metrics[0]
        self.assertEqual(metric.name, "testhistogram")
        self.assertEqual(
            metric.data.data_points[0].explicit_bounds, (1.0, 2.0, 3.0)
        )

    def test_explicit_aggregation_multiple_histograms(self):
        reader = InMemoryMetricReader(
            preferred_aggregation={
                Histogram: ExplicitBucketHistogramAggregation()
            }
        )
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
        self.assertEqual(
            len(metrics.resource_metrics[0].scope_metrics[0].metrics), 2
        )
        metric1 = metrics.resource_metrics[0].scope_metrics[0].metrics[0]
        self.assertEqual(metric1.name, "testhistogram1")
        self.assertEqual(
            metric1.data.data_points[0].explicit_bounds, (1.0, 2.0, 3.0)
        )
        metric2 = metrics.resource_metrics[0].scope_metrics[0].metrics[1]
        self.assertEqual(metric2.name, "testhistogram2")
        self.assertEqual(
            metric2.data.data_points[0].explicit_bounds, (4.0, 5.0, 6.0)
        )

    def test_explicit_aggregation_default_boundaries(self):
        reader = InMemoryMetricReader(
            preferred_aggregation={
                Histogram: ExplicitBucketHistogramAggregation()
            }
        )
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
        self.assertEqual(
            len(metrics.resource_metrics[0].scope_metrics[0].metrics), 1
        )
        metric = metrics.resource_metrics[0].scope_metrics[0].metrics[0]
        self.assertEqual(metric.name, "testhistogram")
        self.assertEqual(
            metric.data.data_points[0].explicit_bounds,
            _DEFAULT_EXPLICIT_BUCKET_HISTOGRAM_AGGREGATION_BOUNDARIES,
        )
