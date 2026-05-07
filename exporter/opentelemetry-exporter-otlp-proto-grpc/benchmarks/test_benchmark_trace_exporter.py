# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=invalid-name

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
