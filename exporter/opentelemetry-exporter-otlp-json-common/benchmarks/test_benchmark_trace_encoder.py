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

import pytest

from opentelemetry.exporter.otlp.json.common.trace_encoder import encode_spans
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Event, SpanContext
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import Link
from opentelemetry.trace.status import Status, StatusCode

from tests import BASE_TIME, TRACE_ID, make_span


def test_benchmark_encode_span_with_events_and_links(benchmark):
    link_ctx = SpanContext(TRACE_ID, 0x2222222222222222, is_remote=False)
    span = make_span(
        events=tuple(
            Event(
                name=f"event_{i}",
                timestamp=BASE_TIME + i * 10**6,
                attributes={"event_key": f"val_{i}"},
            )
            for i in range(5)
        ),
        links=tuple(
            Link(context=link_ctx, attributes={"link_key": True})
            for _ in range(3)
        ),
        resource=Resource({"service.name": "bench-svc"}),
        instrumentation_scope=InstrumentationScope("bench_lib", "1.0"),
    )
    span._status = Status(StatusCode.ERROR, "benchmark error")

    benchmark(encode_spans, [span])


@pytest.mark.parametrize("batch_size", [1, 10, 100])
def test_benchmark_encode_spans(benchmark, batch_size):
    spans = [
        make_span(name=f"span-{i}", span_id=0x1000 + i)
        for i in range(batch_size)
    ]

    benchmark(encode_spans, spans)
