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

from itertools import count
from logging import ERROR
from platform import system
from time import sleep
from unittest import TestCase

from pytest import mark

from opentelemetry.context import Context
from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import Counter, MeterProvider, ObservableCounter
from opentelemetry.sdk.metrics._internal.exemplar import AlwaysOnExemplarFilter
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    InMemoryMetricReader,
)
from opentelemetry.sdk.metrics.view import SumAggregation


class TestSumAggregation(TestCase):
    @mark.skipif(
        system() != "Linux",
        reason=(
            "Tests fail because Windows time_ns resolution is too low so "
            "two different time measurements may end up having the exact same"
            "value."
        ),
    )
    def test_asynchronous_delta_temporality(self):
        eight_multiple_generator = count(start=8, step=8)

        counter = 0

        def observable_counter_callback(callback_options):
            nonlocal counter
            counter += 1

            if counter < 11:
                yield

            elif counter < 21:
                yield Observation(next(eight_multiple_generator))

            else:
                yield

        aggregation = SumAggregation()

        reader = InMemoryMetricReader(
            preferred_aggregation={ObservableCounter: aggregation},
            preferred_temporality={
                ObservableCounter: AggregationTemporality.DELTA
            },
        )

        provider = MeterProvider(metric_readers=[reader])
        meter = provider.get_meter("name", "version")

        meter.create_observable_counter(
            "observable_counter", [observable_counter_callback]
        )

        results = []

        for _ in range(10):
            with self.assertLogs(level=ERROR):
                results.append(reader.get_metrics_data())

        self.assertEqual(counter, 10)

        for metrics_data in results:
            self.assertIsNone(metrics_data)

        results = []

        for _ in range(10):
            results.append(reader.get_metrics_data())

        self.assertEqual(counter, 20)

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
                .value
            ),
            8,
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

        for metrics_data in results[1:]:
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
            self.assertEqual(metric_data.value, 8)
            self.assertLess(
                metric_data.start_time_unix_nano, metric_data.time_unix_nano
            )

        results = []

        for _ in range(10):
            with self.assertLogs(level=ERROR):
                results.append(reader.get_metrics_data())

        self.assertEqual(counter, 30)

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
    def test_asynchronous_cumulative_temporality(self):
        eight_multiple_generator = count(start=8, step=8)

        counter = 0

        def observable_counter_callback(callback_options):
            nonlocal counter
            counter += 1

            if counter < 11:
                yield

            elif counter < 21:
                yield Observation(next(eight_multiple_generator))

            else:
                yield

        aggregation = SumAggregation()

        reader = InMemoryMetricReader(
            preferred_aggregation={ObservableCounter: aggregation},
            preferred_temporality={
                ObservableCounter: AggregationTemporality.CUMULATIVE
            },
        )

        provider = MeterProvider(metric_readers=[reader])
        meter = provider.get_meter("name", "version")

        meter.create_observable_counter(
            "observable_counter", [observable_counter_callback]
        )

        results = []

        for _ in range(10):
            with self.assertLogs(level=ERROR):
                results.append(reader.get_metrics_data())

        self.assertEqual(counter, 10)

        for metrics_data in results:
            self.assertIsNone(metrics_data)

        results = []

        for _ in range(10):
            results.append(reader.get_metrics_data())

        self.assertEqual(counter, 20)

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
            self.assertEqual(metric_data.value, 8 * (index + 1))

        results = []

        for _ in range(10):
            with self.assertLogs(level=ERROR):
                results.append(reader.get_metrics_data())

        self.assertEqual(counter, 30)

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
    def test_synchronous_delta_temporality(self):
        aggregation = SumAggregation()

        reader = InMemoryMetricReader(
            preferred_aggregation={Counter: aggregation},
            preferred_temporality={Counter: AggregationTemporality.DELTA},
        )

        provider = MeterProvider(metric_readers=[reader])
        meter = provider.get_meter("name", "version")

        counter = meter.create_counter("counter")

        results = []

        for _ in range(10):
            results.append(reader.get_metrics_data())

        for metrics_data in results:
            self.assertIsNone(metrics_data)

        results = []

        for _ in range(10):
            counter.add(8)
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
                .value
            ),
            8,
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

        for metrics_data in results[1:]:
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
            self.assertEqual(metric_data.value, 8)
            self.assertLess(
                metric_data.start_time_unix_nano, metric_data.time_unix_nano
            )

        results = []

        for _ in range(10):
            results.append(reader.get_metrics_data())

        for metrics_data in results:
            self.assertIsNone(metrics_data)

        results = []

        counter.add(1)
        results.append(reader.get_metrics_data())

        sleep(0.1)
        results.append(reader.get_metrics_data())

        counter.add(2)
        results.append(reader.get_metrics_data())

        metric_data_0 = (
            results[0]
            .resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points[0]
        )
        metric_data_2 = (
            results[2]
            .resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points[0]
        )

        self.assertIsNone(results[1])

        self.assertGreater(
            metric_data_2.start_time_unix_nano, metric_data_0.time_unix_nano
        )

        provider.shutdown()

    @mark.skipif(
        system() != "Linux",
        reason=(
            "Tests fail because Windows time_ns resolution is too low so "
            "two different time measurements may end up having the exact same"
            "value."
        ),
    )
    def test_synchronous_cumulative_temporality(self):
        aggregation = SumAggregation()

        reader = InMemoryMetricReader(
            preferred_aggregation={Counter: aggregation},
            preferred_temporality={Counter: AggregationTemporality.CUMULATIVE},
        )

        provider = MeterProvider(metric_readers=[reader])
        meter = provider.get_meter("name", "version")

        counter = meter.create_counter("counter")

        results = []

        for _ in range(10):
            results.append(reader.get_metrics_data())

        for metrics_data in results:
            self.assertIsNone(metrics_data)

        results = []

        for _ in range(10):
            counter.add(8)
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
            self.assertEqual(metric_data.value, 8 * (index + 1))

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
            self.assertEqual(metric_data.value, 80)

    def test_sum_aggregation_with_exemplars(self):
        in_memory_metric_reader = InMemoryMetricReader()

        provider = MeterProvider(
            metric_readers=[in_memory_metric_reader],
            exemplar_filter=AlwaysOnExemplarFilter(),
        )

        meter = provider.get_meter("my-meter")
        counter = meter.create_counter("my_counter")

        counter.add(2, {"attribute": "value1"}, context=Context())
        counter.add(5, {"attribute": "value2"}, context=Context())
        counter.add(3, {"attribute": "value3"}, context=Context())

        metric_data = in_memory_metric_reader.get_metrics_data()

        self.assertEqual(
            len(metric_data.resource_metrics[0].scope_metrics[0].metrics), 1
        )

        sum_metric = (
            metric_data.resource_metrics[0].scope_metrics[0].metrics[0]
        )

        data_points = sum_metric.data.data_points
        self.assertEqual(len(data_points), 3)

        self.assertEqual(data_points[0].exemplars[0].value, 2.0)
        self.assertEqual(data_points[1].exemplars[0].value, 5.0)
        self.assertEqual(data_points[2].exemplars[0].value, 3.0)

        provider.shutdown()
