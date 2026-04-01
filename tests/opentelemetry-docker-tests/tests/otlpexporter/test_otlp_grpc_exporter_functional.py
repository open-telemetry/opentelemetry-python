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
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.test.test_base import TestBase

from . import (
    BaseTestOTLPExporter,
    ExportStatusMetricReader,
    ExportStatusSpanProcessor,
)


class TestOTLPGRPCExporter(BaseTestOTLPExporter, TestBase):
    # pylint: disable=no-self-use
    def get_span_processor(self):
        return ExportStatusSpanProcessor(
            OTLPSpanExporter(insecure=True, timeout=1)
        )

    def get_metric_reader(self):
        return ExportStatusMetricReader(
            OTLPMetricExporter(
                insecure=True, timeout=1, max_export_batch_size=2
            )
        )

    def setUp(self):
        super().setUp()

        trace.set_tracer_provider(TracerProvider())
        self.tracer = trace.get_tracer(__name__)
        self.span_processor = self.get_span_processor()
        trace.get_tracer_provider().add_span_processor(self.span_processor)

        self.metric_reader = self.get_metric_reader()
        meter_provider = MeterProvider(metric_readers=[self.metric_reader])
        metrics.set_meter_provider(meter_provider)
        self.meter = metrics.get_meter(__name__)
