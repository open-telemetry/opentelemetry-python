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

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)


class TestConsoleExporter(TestCase):
    def test_console_exporter(self):

        try:
            exporter = ConsoleMetricExporter()
            reader = PeriodicExportingMetricReader(exporter)
            provider = MeterProvider(metric_readers=[reader])
            metrics.set_meter_provider(provider)
            meter = metrics.get_meter(__name__)
            counter = meter.create_counter("test")
            counter.add(1)
        except Exception as error:
            self.fail(f"Unexpected exception {error} raised")
