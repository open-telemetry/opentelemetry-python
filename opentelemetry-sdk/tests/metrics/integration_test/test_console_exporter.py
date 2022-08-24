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

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.test.globals_test import reset_metrics_globals


class TestConsoleExporter(TestCase):
    def test_console_exporter(self):

        reset_metrics_globals()

        output = StringIO()
        exporter = ConsoleMetricExporter(out=output)
        reader = PeriodicExportingMetricReader(
            exporter, export_interval_millis=100
        )
        provider = MeterProvider(metric_readers=[reader])
        metrics.set_meter_provider(provider)
        meter = metrics.get_meter(__name__)
        counter = meter.create_counter(
            "name", description="description", unit="unit"
        )
        counter.add(1, attributes={"a": "b"})
        provider.shutdown()

        output.seek(0)
        result_0 = loads(output.readlines()[0])

        self.assertGreater(len(result_0), 0)
        self.assertEqual(
            result_0["resource_metrics"][0]["scope_metrics"][0]["scope"][
                "name"
            ],
            "test_console_exporter",
        )
        self.assertEqual(
            result_0["resource_metrics"][0]["scope_metrics"][0]["metrics"][0][
                "name"
            ],
            "name",
        )
        self.assertEqual(
            result_0["resource_metrics"][0]["scope_metrics"][0]["metrics"][0][
                "description"
            ],
            "description",
        )
        self.assertEqual(
            result_0["resource_metrics"][0]["scope_metrics"][0]["metrics"][0][
                "unit"
            ],
            "unit",
        )
        self.assertEqual(
            result_0["resource_metrics"][0]["scope_metrics"][0]["metrics"][0][
                "data"
            ]["data_points"][0]["attributes"],
            {"a": "b"},
        )
        self.assertEqual(
            result_0["resource_metrics"][0]["scope_metrics"][0]["metrics"][0][
                "data"
            ]["data_points"][0]["value"],
            1,
        )
        self.assertEqual(
            result_0["resource_metrics"][0]["scope_metrics"][0]["metrics"][0][
                "data"
            ]["aggregation_temporality"],
            2,
        )
        self.assertTrue(
            result_0["resource_metrics"][0]["scope_metrics"][0]["metrics"][0][
                "data"
            ]["is_monotonic"]
        )
