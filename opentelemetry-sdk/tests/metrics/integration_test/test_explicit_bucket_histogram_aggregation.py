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

from platform import system
from unittest import TestCase

from pytest import mark

from opentelemetry.sdk.metrics import Histogram, MeterProvider
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    InMemoryMetricReader,
)
from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation


class TestExplicitBucketHistogramAggregation(TestCase):

    values = [
        1.0,
        6.0,
        11.0,
        26.0,
        51.0,
        76.0,
        101.0,
        251.0,
        501.0,
        751.0,
    ]

    @mark.skipif(
        system() != "Linux",
        reason=(
            "Tests fail because Windows time_ns resolution is too low so "
            "two different time measurements may end up having the exact same"
            "value."
        ),
    )
    def test_synchronous_delta_temporality(self):

        aggregation = ExplicitBucketHistogramAggregation()

        reader = InMemoryMetricReader(
            preferred_aggregation={Histogram: aggregation},
            preferred_temporality={Histogram: AggregationTemporality.DELTA},
        )

        provider = MeterProvider(metric_readers=[reader])
        meter = provider.get_meter("name", "version")

        histogram = meter.create_histogram("histogram")

        results = []

        for _ in range(10):

            results.append(reader.get_metrics_data())

        for metrics_data in results:
            self.assertIsNone(metrics_data)

        results = []

        for value in self.values:
            histogram.record(value)
            results.append(reader.get_metrics_data())

        previous_time_unix_nano = (
            results[0]
            .resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points[0]
            .time_unix_nano
        )

        self.assertEqual(
            (
                results[0]
                .resource_metrics[0]
                .scope_metrics[0]
                .metrics[0]
                .data.data_points[0]
                .bucket_counts
            ),
            (0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        )

        self.assertLess(
            (
                results[0]
                .resource_metrics[0]
                .scope_metrics[0]
                .metrics[0]
                .data.data_points[0]
                .start_time_unix_nano
            ),
            previous_time_unix_nano,
        )

        for index, metrics_data in enumerate(results[1:]):

            metric_data = (
                metrics_data.resource_metrics[0]
                .scope_metrics[0]
                .metrics[0]
                .data.data_points[0]
            )

            self.assertEqual(
                previous_time_unix_nano, metric_data.start_time_unix_nano
            )
            previous_time_unix_nano = metric_data.time_unix_nano

            self.assertEqual(
                metric_data.bucket_counts,
                tuple([1 if value == index + 2 else 0 for value in range(16)]),
            )
            self.assertLess(
                metric_data.start_time_unix_nano, metric_data.time_unix_nano
            )

        results = []

        for _ in range(10):

            results.append(reader.get_metrics_data())

        provider.shutdown()

        for metrics_data in results:
            self.assertIsNone(metrics_data)

    @mark.skipif(
        system() != "Linux",
        reason=(
            "Tests fail because Windows time_ns resolution is too low so "
            "two different time measurements may end up having the exact same"
            "value."
        ),
    )
    def test_synchronous_cumulative_temporality(self):

        aggregation = ExplicitBucketHistogramAggregation()

        reader = InMemoryMetricReader(
            preferred_aggregation={Histogram: aggregation},
            preferred_temporality={
                Histogram: AggregationTemporality.CUMULATIVE
            },
        )

        provider = MeterProvider(metric_readers=[reader])
        meter = provider.get_meter("name", "version")

        histogram = meter.create_histogram("histogram")

        results = []

        for _ in range(10):

            results.append(reader.get_metrics_data())

        for metrics_data in results:
            self.assertIsNone(metrics_data)

        results = []

        for value in self.values:
            histogram.record(value)
            results.append(reader.get_metrics_data())

        start_time_unix_nano = (
            results[0]
            .resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points[0]
            .start_time_unix_nano
        )

        for index, metrics_data in enumerate(results):

            metric_data = (
                metrics_data.resource_metrics[0]
                .scope_metrics[0]
                .metrics[0]
                .data.data_points[0]
            )

            self.assertEqual(
                start_time_unix_nano, metric_data.start_time_unix_nano
            )
            self.assertEqual(
                metric_data.bucket_counts,
                tuple(
                    [
                        1
                        if inner_index <= index + 1 and inner_index > 0
                        else 0
                        for inner_index, value in enumerate(range(16))
                    ]
                ),
            )

        results = []

        for _ in range(10):

            results.append(reader.get_metrics_data())

        provider.shutdown()

        start_time_unix_nano = (
            results[0]
            .resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points[0]
            .start_time_unix_nano
        )

        for metrics_data in results:

            metric_data = (
                metrics_data.resource_metrics[0]
                .scope_metrics[0]
                .metrics[0]
                .data.data_points[0]
            )

            self.assertEqual(
                start_time_unix_nano, metric_data.start_time_unix_nano
            )
            self.assertEqual(
                metric_data.bucket_counts,
                (0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0),
            )
