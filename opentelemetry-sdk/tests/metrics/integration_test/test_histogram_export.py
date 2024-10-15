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
from opentelemetry.sdk.metrics._internal.exemplar import (
    AlwaysOffExemplarFilter,
    AlwaysOnExemplarFilter,
)
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource


class TestHistogramExport(TestCase):
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

        self.assertEqual(
            len(metric_data.resource_metrics[0].scope_metrics[0].metrics), 2
        )

        self.assertEqual(
            (
                metric_data.resource_metrics[0]
                .scope_metrics[0]
                .metrics[0]
                .data.data_points[0]
                .bucket_counts
            ),
            (0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        )
        self.assertEqual(
            (
                metric_data.resource_metrics[0]
                .scope_metrics[0]
                .metrics[1]
                .data.data_points[0]
                .value
            ),
            1,
        )

        metric_data = in_memory_metric_reader.get_metrics_data()

        self.assertEqual(
            len(metric_data.resource_metrics[0].scope_metrics[0].metrics), 2
        )
        self.assertEqual(
            (
                metric_data.resource_metrics[0]
                .scope_metrics[0]
                .metrics[0]
                .data.data_points[0]
                .bucket_counts
            ),
            (0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        )
        self.assertEqual(
            (
                metric_data.resource_metrics[0]
                .scope_metrics[0]
                .metrics[1]
                .data.data_points[0]
                .value
            ),
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

        histogram.record(
            2, {"attribute": "value1"}
        )  # Should go in the first bucket
        histogram.record(
            7, {"attribute": "value2"}
        )  # Should go in the second bucket
        histogram.record(
            9, {"attribute": "value2"}
        )  # Should also go in the second bucket
        histogram.record(
            15, {"attribute": "value3"}
        )  # Should go in the third bucket

        metric_data = in_memory_metric_reader.get_metrics_data()

        self.assertEqual(
            len(metric_data.resource_metrics[0].scope_metrics[0].metrics), 1
        )
        histogram_metric = (
            metric_data.resource_metrics[0].scope_metrics[0].metrics[0]
        )

        self.assertEqual(len(histogram_metric.data.data_points), 3)

        self.assertEqual(
            len(histogram_metric.data.data_points[0].exemplars), 1
        )
        self.assertEqual(
            len(histogram_metric.data.data_points[1].exemplars), 1
        )
        self.assertEqual(
            len(histogram_metric.data.data_points[2].exemplars), 1
        )

        self.assertEqual(histogram_metric.data.data_points[0].sum, 2)
        self.assertEqual(histogram_metric.data.data_points[1].sum, 16)
        self.assertEqual(histogram_metric.data.data_points[2].sum, 15)

        self.assertEqual(
            histogram_metric.data.data_points[0].exemplars[0].value, 2.0
        )
        self.assertEqual(
            histogram_metric.data.data_points[1].exemplars[0].value, 9.0
        )
        self.assertEqual(
            histogram_metric.data.data_points[2].exemplars[0].value, 15.0
        )

    def test_filter_with_exemplars(self):
        in_memory_metric_reader = InMemoryMetricReader()

        provider = MeterProvider(
            resource=Resource.create({SERVICE_NAME: "otel-test"}),
            metric_readers=[in_memory_metric_reader],
            exemplar_filter=AlwaysOffExemplarFilter(),
        )
        meter = provider.get_meter("my-meter")
        histogram = meter.create_histogram("my_histogram")

        histogram.record(
            2, {"attribute": "value1"}
        )  # Should go in the first bucket
        histogram.record(
            7, {"attribute": "value2"}
        )  # Should go in the second bucket

        metric_data = in_memory_metric_reader.get_metrics_data()

        self.assertEqual(
            len(metric_data.resource_metrics[0].scope_metrics[0].metrics), 1
        )
        histogram_metric = (
            metric_data.resource_metrics[0].scope_metrics[0].metrics[0]
        )

        self.assertEqual(len(histogram_metric.data.data_points), 2)

        self.assertEqual(
            len(histogram_metric.data.data_points[0].exemplars), 0
        )
        self.assertEqual(
            len(histogram_metric.data.data_points[1].exemplars), 0
        )
