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

from opentelemetry.exporter.otlp import OTLPSpanExporter
from opentelemetry.exporter.otlp.util import Protocol
from opentelemetry.sdk.trace import TracerProvider, sampling
from opentelemetry.sdk.trace.export import (
    BatchExportSpanProcessor,
    SimpleExportSpanProcessor,
)


def get_tracer_with_processor(span_processor_class):
    span_processor = span_processor_class(
        OTLPSpanExporter(Protocol.HTTP_PROTOBUF)
    )
    tracer = TracerProvider(
        active_span_processor=span_processor, sampler=sampling.DEFAULT_ON,
    ).get_tracer("pipeline_benchmark_tracer")
    return tracer


def mocked_requests_post(*args, **kwargs):
    class MockResponse:
        def __init__(self):
            self.status_code = 200

    return MockResponse()


@patch("requests.post", side_effect=mocked_requests_post)
def test_simple_span_processor(mock_post, benchmark):
    tracer = get_tracer_with_processor(SimpleExportSpanProcessor)

    def create_spans_to_be_exported():
        span = tracer.start_span("benchmarkedSpan",)
        for benchmark_span_id in range(10):
            span.set_attribute(
                "benchmarkAttribute_{}".format(benchmark_span_id),
                "benchmarkAttrValue_{}".format(benchmark_span_id),
            )
        span.end()

    benchmark(create_spans_to_be_exported)


@patch("requests.post", side_effect=mocked_requests_post)
def test_batch_span_processor(mock_post, benchmark):
    """Runs benchmark tests using BatchExportSpanProcessor.

    One particular call by pytest-benchmark will be much more expensive since
    the batch export thread will activate and consume a lot of CPU to process
    all the spans. For this reason, focus on the average measurement. Do not
    focus on the min/max measurements which will be misleading.
    """
    tracer = get_tracer_with_processor(BatchExportSpanProcessor)

    def create_spans_to_be_exported():
        span = tracer.start_span("benchmarkedSpan",)
        for benchmark_span_id in range(10):
            span.set_attribute(
                "benchmarkAttribute_{}".format(benchmark_span_id),
                "benchmarkAttrValue_{}".format(benchmark_span_id),
            )
        span.end()

    benchmark(create_spans_to_be_exported)
