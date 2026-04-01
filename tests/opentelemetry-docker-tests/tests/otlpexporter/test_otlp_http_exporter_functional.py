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

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.test.globals_test import (
    reset_metrics_globals,
    reset_trace_globals,
)
from opentelemetry.test.test_base import TestBase

from . import (
    BaseTestOTLPExporter,
    ExportStatusMetricReader,
    ExportStatusSpanProcessor,
)


class BatchCountingHTTPExporter(OTLPMetricExporter):
    """HTTP exporter that counts actual batch export calls for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.export_call_count = 0

    def _export(self, *args, **kwargs):
        self.export_call_count += 1
        return super()._export(*args, **kwargs)


class TestOTLPHTTPExporter(BaseTestOTLPExporter, TestBase):
    # pylint: disable=no-self-use
    def get_span_processor(self):
        return ExportStatusSpanProcessor(OTLPSpanExporter())

    def get_metric_reader(self):
        return ExportStatusMetricReader(
            OTLPMetricExporter(max_export_batch_size=2)
        )

    def setUp(self):
        super().setUp()

        reset_trace_globals()
        trace.set_tracer_provider(TracerProvider())
        self.tracer = trace.get_tracer(__name__)
        self.span_processor = self.get_span_processor()
        trace.get_tracer_provider().add_span_processor(self.span_processor)

        reset_metrics_globals()
        self.metric_reader = self.get_metric_reader()
        meter_provider = MeterProvider(metric_readers=[self.metric_reader])
        metrics.set_meter_provider(meter_provider)
        self.meter = metrics.get_meter(__name__)

    def test_metrics_export_batch_size_two(self):
        """Test metrics max_export_batch_size=2 directly through HTTP exporter"""
        batch_counter = BatchCountingHTTPExporter(
            endpoint="http://localhost:4318/v1/metrics",
            max_export_batch_size=2,
        )
        metrics_data, data_points = self._create_test_metrics_data(
            num_data_points=6
        )
        result = batch_counter.export(metrics_data)
        self._verify_batch_export_result(
            result, data_points, batch_counter, max_batch_size=2
        )
