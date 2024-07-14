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

from unittest.mock import patch

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.trace import TracerProvider, sampling
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
)


def get_tracer_with_processor(span_processor_class):
    span_processor = span_processor_class(OTLPSpanExporter())
    tracer = TracerProvider(
        active_span_processor=span_processor,
        sampler=sampling.DEFAULT_ON,
    ).get_tracer("pipeline_benchmark_tracer")
    return tracer


class MockTraceServiceStub:
    def __init__(self, channel):
        self.Export = lambda *args, **kwargs: None


@patch(
    "opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter._stub",
    new=MockTraceServiceStub,
)
def test_simple_span_processor(benchmark):
    tracer = get_tracer_with_processor(SimpleSpanProcessor)

    def create_spans_to_be_exported():
        span = tracer.start_span(
            "benchmarkedSpan",
        )
        for i in range(10):
            span.set_attribute(
                f"benchmarkAttribute_{i}",
                f"benchmarkAttrValue_{i}",
            )
        span.end()

    benchmark(create_spans_to_be_exported)


@patch(
    "opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter._stub",
    new=MockTraceServiceStub,
)
def test_batch_span_processor(benchmark):
    """Runs benchmark tests using BatchSpanProcessor.

    One particular call by pytest-benchmark will be much more expensive since
    the batch export thread will activate and consume a lot of CPU to process
    all the spans. For this reason, focus on the average measurement. Do not
    focus on the min/max measurements which will be misleading.
    """
    tracer = get_tracer_with_processor(BatchSpanProcessor)

    def create_spans_to_be_exported():
        span = tracer.start_span(
            "benchmarkedSpan",
        )
        for i in range(10):
            span.set_attribute(
                f"benchmarkAttribute_{i}",
                f"benchmarkAttrValue_{i}",
            )
        span.end()

    benchmark(create_spans_to_be_exported)
