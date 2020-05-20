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

from opentelemetry import metrics, trace
from opentelemetry.context import attach, detach, set_value
from opentelemetry.ext.opencensusexporter.metrics_exporter import (
    OpenCensusMetricsExporter,
)
from opentelemetry.ext.opencensusexporter.trace_exporter import (
    OpenCensusSpanExporter,
)
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export.controller import PushController
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor
from opentelemetry.test.test_base import TestBase


class ExportStatusSpanProcessor(SimpleExportSpanProcessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.export_status = []

    def on_end(self, span):
        token = attach(set_value("suppress_instrumentation", True))
        self.export_status.append(self.span_exporter.export((span,)))
        detach(token)


class ExportStatusMetricController(PushController):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.export_status = []

    def run(self):
        while not self.finished.wait(self.interval):
            self.tick()

    def tick(self):
        # Collect all of the meter's metrics to be exported
        self.meter.collect()
        token = attach(set_value("suppress_instrumentation", True))
        # Export the given metrics in the batcher
        self.export_status.append(
            self.exporter.export(self.meter.batcher.checkpoint_set())
        )
        detach(token)
        # Perform post-exporting logic based on batcher configuration
        self.meter.batcher.finished_collection()


class TestOpenCensusSpanExporter(TestBase):
    def setUp(self):
        super().setUp()

        trace.set_tracer_provider(TracerProvider())
        self.tracer = trace.get_tracer(__name__)
        self.span_processor = ExportStatusSpanProcessor(
            OpenCensusSpanExporter(
                service_name="basic-service", endpoint="localhost:55678"
            )
        )

        trace.get_tracer_provider().add_span_processor(self.span_processor)

    def test_export(self):
        with self.tracer.start_as_current_span("foo"):
            with self.tracer.start_as_current_span("bar"):
                with self.tracer.start_as_current_span("baz"):
                    pass

        self.assertTrue(len(self.span_processor.export_status), 3)

        for export_status in self.span_processor.export_status:
            self.assertEqual(export_status.name, "SUCCESS")
            self.assertEqual(export_status.value, 0)


class TestOpenCensusMetricsExporter(TestBase):
    def setUp(self):
        super().setUp()

        metrics.set_meter_provider(MeterProvider())
        self.meter = metrics.get_meter(__name__)
        self.controller = ExportStatusMetricController(
            self.meter,
            OpenCensusMetricsExporter(
                service_name="basic-service", endpoint="localhost:55678"
            ),
            1,
        )

    def test_export(self):

        self.meter.create_metric(
            name="requests",
            description="number of requests",
            unit="1",
            value_type=int,
            metric_type=Counter,
            label_keys=("environment",),
        ).add(25, {"environment": "staging"})

        sleep(2)

        self.assertEqual(len(self.controller.export_status), 1)
        self.assertEqual(self.controller.export_status[0].name, "SUCCESS")
        self.assertEqual(self.controller.export_status[0].value, 0)
