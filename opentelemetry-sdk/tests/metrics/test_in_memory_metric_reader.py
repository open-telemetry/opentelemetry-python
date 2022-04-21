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
from unittest.mock import Mock

from opentelemetry._metrics.observation import Observation
from opentelemetry.sdk._metrics import MeterProvider
from opentelemetry.sdk._metrics.export import InMemoryMetricReader
from opentelemetry.sdk._metrics.point import (
    AggregationTemporality,
    Metric,
    Sum,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope


class TestInMemoryMetricReader(TestCase):
    def test_no_metrics(self):
        mock_collect_callback = Mock(return_value=[])
        reader = InMemoryMetricReader()
        reader._set_collect_callback(mock_collect_callback)
        self.assertEqual(reader.get_metrics(), [])
        mock_collect_callback.assert_called_once()

    def test_converts_metrics_to_list(self):
        metric = Metric(
            attributes={"myattr": "baz"},
            description="",
            instrumentation_scope=InstrumentationScope("testmetrics"),
            name="foo",
            resource=Resource.create(),
            unit="",
            point=Sum(
                start_time_unix_nano=1647626444152947792,
                time_unix_nano=1647626444153163239,
                value=72.3309814450449,
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
                is_monotonic=True,
            ),
        )
        mock_collect_callback = Mock(return_value=(metric,))
        reader = InMemoryMetricReader()
        reader._set_collect_callback(mock_collect_callback)

        returned_metrics = reader.get_metrics()
        mock_collect_callback.assert_called_once()
        self.assertIsInstance(returned_metrics, list)
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
            "observable_gauge1", callbacks=[lambda: [Observation(value=12)]]
        )
        counter1.add(1, {"foo": "1"})
        counter1.add(1, {"foo": "2"})

        metrics = reader.get_metrics()
        # should be 3 metrics, one from the observable gauge and one for each labelset from the counter
        self.assertEqual(len(metrics), 3)
