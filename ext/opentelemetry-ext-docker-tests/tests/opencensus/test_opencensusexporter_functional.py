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

from opentelemetry.ext.opencensusexporter.metrics_exporter import (
    OpenCensusMetricsExporter,
)
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.test.test_base import TestBase


class TestOpenCensusExporter(TestBase):

    def setUp(self):
        super().setUp()

        exporter = OpenCensusMetricsExporter(
            service_name="basic-service", endpoint="localhost:55678"
        )
        trace.set_tracer_provider(TracerProvider())
        self.tracer = trace.get_tracer(__name__)
        span_processor = BatchExportSpanProcessor(exporter)

        trace.get_tracer_provider().add_span_processor(span_processor)

    def test_long_command(self):
        with self.tracer.start_as_current_span("foo"):
            with self.tracer.start_as_current_span("bar"):
                with self.tracer.start_as_current_span("baz"):
                    print("Hello world from OpenTelemetry Python!")
