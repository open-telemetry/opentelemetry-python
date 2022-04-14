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


import time
from typing import Sequence
from unittest import TestCase

from opentelemetry._metrics.instrument import Counter
from opentelemetry.sdk._metrics import MeterProvider
from opentelemetry.sdk._metrics.aggregation import SumAggregation
from opentelemetry.sdk._metrics.export import (
    MetricExporter,
    MetricExportResult,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk._metrics.point import Metric
from opentelemetry.sdk._metrics.view import View
from opentelemetry.sdk.resources import Resource


class InMemoryMetricExporter(MetricExporter):
    def __init__(self):
        self.metrics = {}
        self._counter = 0

    def export(self, metrics: Sequence[Metric]) -> MetricExportResult:
        self.metrics[self._counter] = metrics
        self._counter += 1
        return MetricExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


class TestDuplicateInstrumentAggregateData(TestCase):
    def test_duplicate_instrument_aggregate_data(self):

        exporter = InMemoryMetricExporter()
        reader = PeriodicExportingMetricReader(
            exporter, export_interval_millis=500
        )
        view = View(
            instrument_type=Counter,
            attribute_keys=[],
            aggregation=SumAggregation(),
        )
        provider = MeterProvider(
            metric_readers=[reader],
            resource=Resource.create(),
            views=[view],
        )

        meter_0 = provider.get_meter(
            name="meter_0",
            version="version",
            schema_url="schema_url",
        )
        meter_1 = provider.get_meter(
            name="meter_1",
            version="version",
            schema_url="schema_url",
        )
        counter_0_0 = meter_0.create_counter(
            "counter", unit="unit", description="description"
        )
        counter_0_1 = meter_0.create_counter(
            "counter", unit="unit", description="description"
        )
        counter_1_0 = meter_1.create_counter(
            "counter", unit="unit", description="description"
        )

        self.assertIs(counter_0_0, counter_0_1)
        self.assertIsNot(counter_0_0, counter_1_0)

        counter_0_0.add(1, {})
        counter_0_1.add(2, {})

        counter_1_0.add(7, {})

        time.sleep(1)

        reader.shutdown()

        metrics = exporter.metrics[0]

        self.assertEqual(len(metrics), 2)

        metric_0 = metrics[0]

        self.assertEqual(metric_0.name, "counter")
        self.assertEqual(metric_0.unit, "unit")
        self.assertEqual(metric_0.description, "description")
        self.assertEqual(metric_0.point.value, 3)

        metric_1 = metrics[1]

        self.assertEqual(metric_1.name, "counter")
        self.assertEqual(metric_1.unit, "unit")
        self.assertEqual(metric_1.description, "description")
        self.assertEqual(metric_1.point.value, 7)
