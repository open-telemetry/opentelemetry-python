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
from abc import ABC, abstractmethod

from opentelemetry.context import attach, detach, set_value
from opentelemetry.sdk.metrics._internal.export import (
    MetricExportResult,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.trace.export import SimpleSpanProcessor


class ExportStatusSpanProcessor(SimpleSpanProcessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.export_status = []

    def on_end(self, span):
        token = attach(set_value("suppress_instrumentation", True))
        self.export_status.append(self.span_exporter.export((span,)))
        detach(token)


class ExportStatusMetricReader(PeriodicExportingMetricReader):
    def __init__(self, exporter, **kwargs):
        # Very short export interval for testing
        super().__init__(exporter, export_interval_millis=1, **kwargs)
        self.export_status = []

    def _receive_metrics(self, metrics_data, timeout_millis=10_000, **kwargs):
        token = attach(set_value("suppress_instrumentation", True))
        try:
            export_result = self._exporter.export(
                metrics_data, timeout_millis=timeout_millis
            )
            self.export_status.append(export_result)
        except Exception:
            self.export_status.append(MetricExportResult.FAILURE)
        finally:
            detach(token)


class BaseTestOTLPExporter(ABC):
    @abstractmethod
    def get_span_processor(self):
        pass

    # pylint: disable=no-member
    def test_export(self):
        with self.tracer.start_as_current_span("foo"):
            with self.tracer.start_as_current_span("bar"):
                with self.tracer.start_as_current_span("baz"):
                    pass

        self.assertTrue(len(self.span_processor.export_status), 3)

        for export_status in self.span_processor.export_status:
            self.assertEqual(export_status.name, "SUCCESS")
            self.assertEqual(export_status.value, 0)

    def test_metrics_export(self):
        counter = self.meter.create_counter("test_counter")
        histogram = self.meter.create_histogram("test_histogram")
        up_down_counter = self.meter.create_up_down_counter(
            "test_up_down_counter"
        )

        counter.add(1, {"key1": "value1"})
        counter.add(2, {"key2": "value2"})
        histogram.record(1.5, {"key3": "value3"})
        histogram.record(2.5, {"key4": "value4"})
        up_down_counter.add(3, {"key5": "value5"})
        up_down_counter.add(-1, {"key6": "value6"})
        self.metric_reader.force_flush(timeout_millis=5000)
        time.sleep(0.1)

        # Verify at least one export happened
        self.assertTrue(len(self.metric_reader.export_status) >= 1)

        # Verify all exports succeeded
        for export_status in self.metric_reader.export_status:
            self.assertEqual(export_status.name, "SUCCESS")
            self.assertEqual(export_status.value, 0)
