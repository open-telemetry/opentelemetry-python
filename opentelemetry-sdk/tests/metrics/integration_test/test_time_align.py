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
from time import sleep
from unittest import TestCase

from pytest import mark

from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    InMemoryMetricReader,
)


class TestTimeAlign(TestCase):

    # This delay is needed for these tests to pass when they are run in
    # Windows.
    delay = 0.001

    def test_time_align_cumulative(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(metric_readers=[reader])

        meter = meter_provider.get_meter("testmeter")

        counter_0 = meter.create_counter("counter_0")
        counter_1 = meter.create_counter("counter_1")

        counter_0.add(10, {"label": "value1"})
        sleep(self.delay)
        counter_0.add(10, {"label": "value2"})
        sleep(self.delay)
        counter_1.add(10, {"label": "value1"})
        sleep(self.delay)
        counter_1.add(10, {"label": "value2"})

        metrics = reader.get_metrics_data()

        data_points_0_0 = list(
            metrics.resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points
        )
        data_points_0_1 = list(
            metrics.resource_metrics[0]
            .scope_metrics[0]
            .metrics[1]
            .data.data_points
        )
        self.assertEqual(len(data_points_0_0), 2)
        self.assertEqual(len(data_points_0_1), 2)

        self.assertLess(
            data_points_0_0[0].start_time_unix_nano,
            data_points_0_0[1].start_time_unix_nano,
        )
        self.assertLess(
            data_points_0_1[0].start_time_unix_nano,
            data_points_0_1[1].start_time_unix_nano,
        )
        self.assertNotEqual(
            data_points_0_0[1].start_time_unix_nano,
            data_points_0_1[0].start_time_unix_nano,
        )

        self.assertEqual(
            data_points_0_0[0].time_unix_nano,
            data_points_0_0[1].time_unix_nano,
        )
        self.assertEqual(
            data_points_0_1[0].time_unix_nano,
            data_points_0_1[1].time_unix_nano,
        )
        self.assertEqual(
            data_points_0_0[1].time_unix_nano,
            data_points_0_1[0].time_unix_nano,
        )

        counter_0.add(10, {"label": "value1"})
        sleep(self.delay)
        counter_0.add(10, {"label": "value2"})
        sleep(self.delay)
        counter_1.add(10, {"label": "value1"})
        sleep(self.delay)
        counter_1.add(10, {"label": "value2"})

        metrics = reader.get_metrics_data()

        data_points_1_0 = list(
            metrics.resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points
        )
        data_points_1_1 = list(
            metrics.resource_metrics[0]
            .scope_metrics[0]
            .metrics[1]
            .data.data_points
        )

        self.assertEqual(len(data_points_1_0), 2)
        self.assertEqual(len(data_points_1_1), 2)

        self.assertLess(
            data_points_1_0[0].start_time_unix_nano,
            data_points_1_0[1].start_time_unix_nano,
        )
        self.assertLess(
            data_points_1_1[0].start_time_unix_nano,
            data_points_1_1[1].start_time_unix_nano,
        )
        self.assertNotEqual(
            data_points_1_0[1].start_time_unix_nano,
            data_points_1_1[0].start_time_unix_nano,
        )

        self.assertEqual(
            data_points_1_0[0].time_unix_nano,
            data_points_1_0[1].time_unix_nano,
        )
        self.assertEqual(
            data_points_1_1[0].time_unix_nano,
            data_points_1_1[1].time_unix_nano,
        )
        self.assertEqual(
            data_points_1_0[1].time_unix_nano,
            data_points_1_1[0].time_unix_nano,
        )

        self.assertEqual(
            data_points_0_0[0].start_time_unix_nano,
            data_points_1_0[0].start_time_unix_nano,
        )
        self.assertEqual(
            data_points_0_0[1].start_time_unix_nano,
            data_points_1_0[1].start_time_unix_nano,
        )
        self.assertEqual(
            data_points_0_1[0].start_time_unix_nano,
            data_points_1_1[0].start_time_unix_nano,
        )
        self.assertEqual(
            data_points_0_1[1].start_time_unix_nano,
            data_points_1_1[1].start_time_unix_nano,
        )

    @mark.skipif(
        system() != "Linux", reason="test failing in CI when run in Windows"
    )
    def test_time_align_delta(self):
        reader = InMemoryMetricReader(
            preferred_temporality={Counter: AggregationTemporality.DELTA}
        )
        meter_provider = MeterProvider(metric_readers=[reader])

        meter = meter_provider.get_meter("testmeter")

        counter_0 = meter.create_counter("counter_0")
        counter_1 = meter.create_counter("counter_1")

        counter_0.add(10, {"label": "value1"})
        sleep(self.delay)
        counter_0.add(10, {"label": "value2"})
        sleep(self.delay)
        counter_1.add(10, {"label": "value1"})
        sleep(self.delay)
        counter_1.add(10, {"label": "value2"})

        metrics = reader.get_metrics_data()

        data_points_0_0 = list(
            metrics.resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points
        )
        data_points_0_1 = list(
            metrics.resource_metrics[0]
            .scope_metrics[0]
            .metrics[1]
            .data.data_points
        )
        self.assertEqual(len(data_points_0_0), 2)
        self.assertEqual(len(data_points_0_1), 2)

        self.assertLess(
            data_points_0_0[0].start_time_unix_nano,
            data_points_0_0[1].start_time_unix_nano,
        )
        self.assertLess(
            data_points_0_1[0].start_time_unix_nano,
            data_points_0_1[1].start_time_unix_nano,
        )
        self.assertNotEqual(
            data_points_0_0[1].start_time_unix_nano,
            data_points_0_1[0].start_time_unix_nano,
        )

        self.assertEqual(
            data_points_0_0[0].time_unix_nano,
            data_points_0_0[1].time_unix_nano,
        )
        self.assertEqual(
            data_points_0_1[0].time_unix_nano,
            data_points_0_1[1].time_unix_nano,
        )
        self.assertEqual(
            data_points_0_0[1].time_unix_nano,
            data_points_0_1[0].time_unix_nano,
        )

        counter_0.add(10, {"label": "value1"})
        sleep(self.delay)
        counter_0.add(10, {"label": "value2"})
        sleep(self.delay)
        counter_1.add(10, {"label": "value1"})
        sleep(self.delay)
        counter_1.add(10, {"label": "value2"})

        metrics = reader.get_metrics_data()

        data_points_1_0 = list(
            metrics.resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points
        )
        data_points_1_1 = list(
            metrics.resource_metrics[0]
            .scope_metrics[0]
            .metrics[1]
            .data.data_points
        )
        self.assertEqual(len(data_points_1_0), 2)
        self.assertEqual(len(data_points_1_1), 2)

        self.assertEqual(
            data_points_1_0[0].start_time_unix_nano,
            data_points_1_0[1].start_time_unix_nano,
        )
        self.assertEqual(
            data_points_1_1[0].start_time_unix_nano,
            data_points_1_1[1].start_time_unix_nano,
        )
        self.assertEqual(
            data_points_1_0[1].start_time_unix_nano,
            data_points_1_1[0].start_time_unix_nano,
        )

        self.assertEqual(
            data_points_1_0[0].time_unix_nano,
            data_points_1_0[1].time_unix_nano,
        )
        self.assertEqual(
            data_points_1_1[0].time_unix_nano,
            data_points_1_1[1].time_unix_nano,
        )
        self.assertEqual(
            data_points_1_0[1].time_unix_nano,
            data_points_1_1[0].time_unix_nano,
        )

        self.assertNotEqual(
            data_points_0_0[0].start_time_unix_nano,
            data_points_1_0[0].start_time_unix_nano,
        )
        self.assertNotEqual(
            data_points_0_0[1].start_time_unix_nano,
            data_points_1_0[1].start_time_unix_nano,
        )
        self.assertNotEqual(
            data_points_0_1[0].start_time_unix_nano,
            data_points_1_1[0].start_time_unix_nano,
        )
        self.assertNotEqual(
            data_points_0_1[1].start_time_unix_nano,
            data_points_1_1[1].start_time_unix_nano,
        )

        self.assertEqual(
            data_points_0_0[0].time_unix_nano,
            data_points_1_0[0].start_time_unix_nano,
        )
        self.assertEqual(
            data_points_0_0[1].time_unix_nano,
            data_points_1_0[1].start_time_unix_nano,
        )
        self.assertEqual(
            data_points_0_1[0].time_unix_nano,
            data_points_1_1[0].start_time_unix_nano,
        )
        self.assertEqual(
            data_points_0_1[1].time_unix_nano,
            data_points_1_1[1].start_time_unix_nano,
        )
