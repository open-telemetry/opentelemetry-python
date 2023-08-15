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

from io import StringIO
from json import loads
from unittest import TestCase

from opentelemetry.metrics import get_meter, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.test.globals_test import reset_metrics_globals


class TestConsoleExporter(TestCase):
    def setUp(self):
        reset_metrics_globals()

    def tearDown(self):
        reset_metrics_globals()

    def test_console_exporter(self):

        output = StringIO()
        exporter = ConsoleMetricExporter(out=output)
        reader = PeriodicExportingMetricReader(
            exporter, export_interval_millis=100
        )
        provider = MeterProvider(metric_readers=[reader])
        set_meter_provider(provider)
        meter = get_meter(__name__)
        counter = meter.create_counter(
            "name", description="description", unit="unit"
        )
        counter.add(1, attributes={"a": "b"})
        provider.shutdown()

        output.seek(0)
        result_0 = loads("".join(output.readlines()))

        self.assertGreater(len(result_0), 0)

        metrics = result_0["resource_metrics"][0]["scope_metrics"][0]

        self.assertEqual(metrics["scope"]["name"], "test_console_exporter")

        metrics = metrics["metrics"][0]

        self.assertEqual(metrics["name"], "name")
        self.assertEqual(metrics["description"], "description")
        self.assertEqual(metrics["unit"], "unit")

        metrics = metrics["data"]

        self.assertEqual(metrics["aggregation_temporality"], 2)
        self.assertTrue(metrics["is_monotonic"])

        metrics = metrics["data_points"][0]

        self.assertEqual(metrics["attributes"], {"a": "b"})
        self.assertEqual(metrics["value"], 1)
