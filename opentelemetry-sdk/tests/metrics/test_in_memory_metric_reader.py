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

# pylint: disable=protected-access

from time import sleep
from unittest import TestCase
from unittest.mock import Mock

from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    InMemoryMetricReader,
    Metric,
    NumberDataPoint,
    Sum,
)


class TestInMemoryMetricReader(TestCase):
    def test_no_metrics(self):
        mock_collect_callback = Mock(return_value=[])
        reader = InMemoryMetricReader()
        reader._set_collect_callback(mock_collect_callback)
        self.assertEqual(reader.get_metrics_data(), [])
        mock_collect_callback.assert_called_once()

    def test_converts_metrics_to_list(self):
        metric = Metric(
            name="foo",
            description="",
            unit="",
            data=Sum(
                data_points=[
                    NumberDataPoint(
                        attributes={"myattr": "baz"},
                        start_time_unix_nano=1647626444152947792,
                        time_unix_nano=1647626444153163239,
                        value=72.3309814450449,
                    )
                ],
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
                is_monotonic=True,
            ),
        )
        mock_collect_callback = Mock(return_value=(metric,))
        reader = InMemoryMetricReader()
        reader._set_collect_callback(mock_collect_callback)

        returned_metrics = reader.get_metrics_data()
        mock_collect_callback.assert_called_once()
        self.assertIsInstance(returned_metrics, tuple)
        self.assertEqual(len(returned_metrics), 1)
        self.assertIs(returned_metrics[0], metric)

    def test_shutdown(self):
        # shutdown should always be successful
        self.assertIsNone(InMemoryMetricReader().shutdown())

    def test_integration(self):
        reader = InMemoryMetricReader()
        meter = MeterProvider(metric_readers=[reader]).get_meter("test_meter")
        counter1 = meter.create_counter("counter1")
        meter.create_observable_gauge(
            "observable_gauge1",
            callbacks=[lambda options: [Observation(value=12)]],
        )
        counter1.add(1, {"foo": "1"})
        counter1.add(1, {"foo": "2"})

        metrics = reader.get_metrics_data()
        # should be 3 number data points, one from the observable gauge and one
        # for each labelset from the counter
        self.assertEqual(len(metrics.resource_metrics[0].scope_metrics), 1)
        self.assertEqual(
            len(metrics.resource_metrics[0].scope_metrics[0].metrics), 2
        )
        self.assertEqual(
            len(
                list(
                    metrics.resource_metrics[0]
                    .scope_metrics[0]
                    .metrics[0]
                    .data.data_points
                )
            ),
            2,
        )
        self.assertEqual(
            len(
                list(
                    metrics.resource_metrics[0]
                    .scope_metrics[0]
                    .metrics[1]
                    .data.data_points
                )
            ),
            1,
        )

    def test_cumulative_multiple_collect(self):

        reader = InMemoryMetricReader(
            preferred_temporality={Counter: AggregationTemporality.CUMULATIVE}
        )
        meter = MeterProvider(metric_readers=[reader]).get_meter("test_meter")
        counter = meter.create_counter("counter1")
        counter.add(1, attributes={"key": "value"})

        reader.collect()

        number_data_point_0 = list(
            reader._metrics_data.resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points
        )[0]

        # Windows tests fail without this sleep because both time_unix_nano
        # values are the same.
        sleep(0.1)
        reader.collect()

        number_data_point_1 = list(
            reader._metrics_data.resource_metrics[0]
            .scope_metrics[0]
            .metrics[0]
            .data.data_points
        )[0]

        self.assertEqual(
            number_data_point_0.attributes, number_data_point_1.attributes
        )
        self.assertEqual(
            number_data_point_0.start_time_unix_nano,
            number_data_point_1.start_time_unix_nano,
        )
        self.assertEqual(
            number_data_point_0.start_time_unix_nano,
            number_data_point_1.start_time_unix_nano,
        )
        self.assertEqual(number_data_point_0.value, number_data_point_1.value)
        self.assertGreater(
            number_data_point_1.time_unix_nano,
            number_data_point_0.time_unix_nano,
        )
