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
from opentelemetry.sdk.metrics.view import (
    ExponentialBucketHistogramAggregation,
)


class TestExponentialBucketHistogramAggregation(TestCase):

    test_values = [2, 4, 1, 1, 8, 0.5, 0.1, 0.045]

    @mark.skipif(
        system() == "Windows",
        reason=(
            "Tests fail because Windows time_ns resolution is too low so "
            "two different time measurements may end up having the exact same"
            "value."
        ),
    )
    def test_synchronous_delta_temporality(self):

        aggregation = ExponentialBucketHistogramAggregation()

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

        for test_value in self.test_values:
            histogram.record(test_value)
            results.append(reader.get_metrics_data())

        metric_data = (
            results[0]
            .resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points[0]
        )

        previous_time_unix_nano = metric_data.time_unix_nano

        self.assertEqual(metric_data.positive.bucket_counts, [1])
        self.assertEqual(metric_data.negative.bucket_counts, [0])

        self.assertLess(
            metric_data.start_time_unix_nano,
            previous_time_unix_nano,
        )
        self.assertEqual(metric_data.min, self.test_values[0])
        self.assertEqual(metric_data.max, self.test_values[0])
        self.assertEqual(metric_data.sum, self.test_values[0])

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
            self.assertEqual(metric_data.positive.bucket_counts, [1])
            self.assertEqual(metric_data.negative.bucket_counts, [0])
            self.assertLess(
                metric_data.start_time_unix_nano, metric_data.time_unix_nano
            )
            self.assertEqual(metric_data.min, self.test_values[index + 1])
            self.assertEqual(metric_data.max, self.test_values[index + 1])
            self.assertEqual(metric_data.sum, self.test_values[index + 1])

        results = []

        for _ in range(10):

            results.append(reader.get_metrics_data())

        provider.shutdown()

        for metrics_data in results:
            self.assertIsNone(metrics_data)

    @mark.skipif(
        system() == "Windows",
        reason=(
            "Tests fail because Windows time_ns resolution is too low so "
            "two different time measurements may end up having the exact same"
            "value."
        ),
    )
    def test_synchronous_cumulative_temporality(self):

        aggregation = ExponentialBucketHistogramAggregation()

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

        for test_value in self.test_values:
            histogram.record(test_value)
            results.append(reader.get_metrics_data())

        metric_data = (
            results[0]
            .resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points[0]
        )

        start_time_unix_nano = metric_data.start_time_unix_nano

        self.assertLess(
            metric_data.start_time_unix_nano,
            metric_data.time_unix_nano,
        )
        self.assertEqual(metric_data.min, self.test_values[0])
        self.assertEqual(metric_data.max, self.test_values[0])
        self.assertEqual(metric_data.sum, self.test_values[0])

        previous_time_unix_nano = metric_data.time_unix_nano

        for index, metrics_data in enumerate(results[1:]):
            metric_data = (
                metrics_data.resource_metrics[0]
                .scope_metrics[0]
                .metrics[0]
                .data.data_points[0]
            )

            self.assertEqual(
                start_time_unix_nano, metric_data.start_time_unix_nano
            )
            self.assertLess(
                metric_data.start_time_unix_nano,
                metric_data.time_unix_nano,
            )
            self.assertEqual(
                metric_data.min, min(self.test_values[: index + 2])
            )
            self.assertEqual(
                metric_data.max, max(self.test_values[: index + 2])
            )
            self.assertEqual(
                metric_data.sum, sum(self.test_values[: index + 2])
            )

            self.assertGreater(
                metric_data.time_unix_nano, previous_time_unix_nano
            )

            previous_time_unix_nano = metric_data.time_unix_nano

        self.assertEqual(
            metric_data.positive.bucket_counts,
            [
                1,
                *[0] * 17,
                1,
                *[0] * 36,
                1,
                *[0] * 15,
                2,
                *[0] * 15,
                1,
                *[0] * 15,
                1,
                *[0] * 15,
                1,
                *[0] * 40,
            ],
        )
        self.assertEqual(metric_data.negative.bucket_counts, [0])

        results = []

        for i in range(10):
            results.append(reader.get_metrics_data())

        provider.shutdown()

        metric_data = (
            results[0]
            .resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points[0]
        )

        start_time_unix_nano = metric_data.start_time_unix_nano

        self.assertLess(
            metric_data.start_time_unix_nano,
            metric_data.time_unix_nano,
        )
        self.assertEqual(metric_data.min, min(self.test_values))
        self.assertEqual(metric_data.max, max(self.test_values))
        self.assertEqual(metric_data.sum, sum(self.test_values))

        previous_metric_data = metric_data

        for index, metrics_data in enumerate(results[1:]):
            metric_data = (
                metrics_data.resource_metrics[0]
                .scope_metrics[0]
                .metrics[0]
                .data.data_points[0]
            )

            self.assertEqual(
                previous_metric_data.start_time_unix_nano,
                metric_data.start_time_unix_nano,
            )
            self.assertEqual(previous_metric_data.min, metric_data.min)
            self.assertEqual(previous_metric_data.max, metric_data.max)
            self.assertEqual(previous_metric_data.sum, metric_data.sum)

            self.assertEqual(
                metric_data.positive.bucket_counts,
                [
                    1,
                    *[0] * 17,
                    1,
                    *[0] * 36,
                    1,
                    *[0] * 15,
                    2,
                    *[0] * 15,
                    1,
                    *[0] * 15,
                    1,
                    *[0] * 15,
                    1,
                    *[0] * 40,
                ],
            )
            self.assertEqual(metric_data.negative.bucket_counts, [0])

            self.assertLess(
                previous_metric_data.time_unix_nano,
                metric_data.time_unix_nano,
            )
