# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

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
