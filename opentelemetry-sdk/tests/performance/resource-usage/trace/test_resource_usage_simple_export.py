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
from unittest import mock

from opentelemetry.exporter.otlp.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider, sampling
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor


SPANS_PER_SECOND = 10_000

simple_span_processor = SimpleExportSpanProcessor(OTLPSpanExporter())
tracer = TracerProvider(
    active_span_processor=simple_span_processor, sampler=sampling.DEFAULT_ON,
).get_tracer("resource_usage_tracer")


class MockTraceServiceStub(object):
    def __init__(self, channel):
        self.Export = lambda *args, **kwargs: None


def test_simple_span_processor():
    patch = mock.patch(
        "opentelemetry.exporter.otlp.trace_exporter.OTLPSpanExporter._stub",
        new=MockTraceServiceStub,
    )
    with patch:
        for i in range(15):
            print("STARTING NUMBER: ", i)
            starttime = time.time()
            while time.time() - starttime < 60:
                print("Difference is: ", time.time() - starttime)
                span = tracer.start_span("benchmarkedSpan")
                print("Do span work")
                span.end()
                print("Finish span work")
            time.sleep(60.0 - ((time.time() - starttime) % 60.0))


test_simple_span_processor()
