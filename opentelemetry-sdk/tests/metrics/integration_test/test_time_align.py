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

from time import sleep
from unittest import TestCase

from opentelemetry.sdk._metrics import MeterProvider
from opentelemetry.sdk._metrics.export import InMemoryMetricReader
from opentelemetry.sdk._metrics.view import View


class TestTimeAlign(TestCase):
    def test_time_align(self):
        reader = InMemoryMetricReader()
        meter_provider = MeterProvider(
            metric_readers=[reader],
            views=[
                View(instrument_name="counter_0"),
                View(instrument_name="counter_1"),
            ],
        )

        meter = meter_provider.get_meter("testmeter")

        counter_0 = meter.create_counter("counter_0")
        counter_1 = meter.create_counter("counter_1")

        counter_0.add(10, {"label": "value1"})
        counter_0.add(10, {"label": "value2"})
        sleep(0.1)
        counter_1.add(10, {"label": "value1"})
        counter_1.add(10, {"label": "value2"})

        metrics = reader.get_metrics_data()

        data_points_0 = list(
            metrics.resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points
        )
        data_points_1 = list(
            metrics.resource_metrics[0]
            .scope_metrics[0]
            .metrics[1]
            .data.data_points
        )
        self.assertEqual(
            data_points_0[0].start_time_unix_nano,
            data_points_0[1].start_time_unix_nano,
        )
        self.assertEqual(
            data_points_1[0].start_time_unix_nano,
            data_points_1[1].start_time_unix_nano,
        )
        self.assertNotEqual(
            data_points_0[1].start_time_unix_nano,
            data_points_1[0].start_time_unix_nano,
        )
