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

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.trace import TracerProvider, sampling
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

TEST_DURATION_SECONDS = 15
SPANS_PER_SECOND = 10_000


class MockTraceServiceStub:
    def __init__(self, channel):
        self.Export = lambda *args, **kwargs: None


old_stub = OTLPSpanExporter._stub
OTLPSpanExporter._stub = MockTraceServiceStub

simple_span_processor = SimpleSpanProcessor(OTLPSpanExporter())
tracer = TracerProvider(
    active_span_processor=simple_span_processor,
    sampler=sampling.DEFAULT_ON,
).get_tracer("resource_usage_tracer")

starttime = time.time()
for _ in range(TEST_DURATION_SECONDS):
    for _ in range(SPANS_PER_SECOND):
        span = tracer.start_span("benchmarkedSpan")
        span.end()
    time_to_finish_spans = time.time() - starttime
    time.sleep(1.0 - time_to_finish_spans if time_to_finish_spans < 1.0 else 0)

OTLPSpanExporter._stub = old_stub
