# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from functools import lru_cache

import pytest

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import (
    ReadableSpan,
    SpanProcessor,
    TracerProvider,
    _default_tracer_configurator,
    _RuleBasedTracerConfigurator,
    _TracerConfig,
    sampling,
)
from opentelemetry.sdk.util.instrumentation import _scope_name_matches_glob
from opentelemetry.trace import SpanContext, TraceFlags

tracer_provider = TracerProvider(
    sampler=sampling.DEFAULT_ON,
    resource=Resource(
        {
            "service.name": "A123456789",
            "service.version": "1.34567890",
            "service.instance.id": "123ab456-a123-12ab-12ab-12340a1abc12",
        }
    ),
)
tracer = tracer_provider.get_tracer("sdk_tracer_provider")


@pytest.fixture(params=[0, 1, 10, 50])
def num_tracer_configurator_rules(request):
    return request.param


def test_simple_start_span(benchmark):
    def benchmark_start_span():
        span = tracer.start_span(
            "benchmarkedSpan",
            attributes={"long.attribute": -10000000001000000000},
        )
        span.add_event("benchmarkEvent")
        span.end()

    benchmark(benchmark_start_span)


@pytest.mark.parametrize("num_attrs", [0, 1, 10, 50, 128])
def test_start_span_with_attributes(benchmark, num_attrs):
    attrs = {f"key{i}": f"value{i}" for i in range(num_attrs)}

    def benchmark_start_span():
        span = tracer.start_span("benchmarkedSpan", attributes=attrs)
        span.end()

    benchmark(benchmark_start_span)


# pylint: disable=protected-access,redefined-outer-name
def test_simple_start_span_with_tracer_configurator_rules(
    benchmark, num_tracer_configurator_rules
):
    def benchmark_start_span():
        span = tracer.start_span(
            "benchmarkedSpan",
            attributes={"long.attribute": -10000000001000000000},
        )
        span.add_event("benchmarkEvent")
        span.end()

    @lru_cache
    def tracer_configurator(tracer_scope):
        # this is testing 100 rules that is an extreme case
        return _RuleBasedTracerConfigurator(
            rules=[
                (
                    _scope_name_matches_glob(glob_pattern=str(i)),
                    _TracerConfig(is_enabled=True),
                )
                for i in range(num_tracer_configurator_rules)
            ],
            default_config=_TracerConfig(is_enabled=True),
        )(tracer_scope)

    tracer_provider._set_tracer_configurator(
        tracer_configurator=tracer_configurator
    )
    benchmark(benchmark_start_span)
    tracer_provider._set_tracer_configurator(
        tracer_configurator=_default_tracer_configurator
    )


@pytest.mark.parametrize("num_attrs", [1, 10, 50, 128])
def test_set_attribute(benchmark, num_attrs):
    attrs = {f"key{i}": f"value{i}" for i in range(num_attrs)}

    def benchmark_set_attribute():
        span = tracer.start_span("benchmarkedSpan")
        for key, value in attrs.items():
            span.set_attribute(key, value)
        span.end()

    benchmark(benchmark_set_attribute)


@pytest.mark.parametrize(
    "attr_type,value",
    [
        ("bool", True),
        ("int", 42),
        ("float", 3.14),
        ("str", "hello world"),
        ("bytes", b"hello world"),
        ("seq_bool", (True, False, True)),
        ("seq_int", (1, 2, 3, 4, 5)),
        ("seq_float", (1.1, 2.2, 3.3)),
        ("seq_str", ("a", "b", "c", "d", "e")),
        ("seq_bytes", (b"a", b"b", b"c")),
    ],
)
def test_set_attribute_types(benchmark, attr_type, value):
    attrs = {f"key{i}": value for i in range(128)}

    def benchmark_set_attribute():
        for _ in range(5_000):
            span = tracer.start_span("benchmarkedSpan")
            for key, val in attrs.items():
                span.set_attribute(key, val)
            span.end()

    benchmark(benchmark_set_attribute)


def test_simple_start_as_current_span(benchmark):
    def benchmark_start_as_current_span():
        with tracer.start_as_current_span(
            "benchmarkedSpan",
            attributes={"long.attribute": -10000000001000000000},
        ) as span:
            span.add_event("benchmarkEvent")

    benchmark(benchmark_start_as_current_span)


class _EventsReadingProcessor(SpanProcessor):
    def on_end(self, span: ReadableSpan) -> None:
        _ = span.events


class _LinksReadingProcessor(SpanProcessor):
    def on_end(self, span: ReadableSpan) -> None:
        _ = span.links


_link_context = SpanContext(
    trace_id=0x000000000000000000000000DEADBEEF,
    span_id=0x00000000DEADBEF0,
    is_remote=True,
    trace_flags=TraceFlags(TraceFlags.SAMPLED),
)


@pytest.mark.parametrize("num_events", [1, 10, 50, 128])
def test_read_events(benchmark, num_events):
    provider = TracerProvider(sampler=sampling.DEFAULT_ON)
    provider.add_span_processor(_EventsReadingProcessor())
    t = provider.get_tracer("bench")

    def benchmark_read_events():
        span = t.start_span("benchmarkedSpan")
        for i in range(num_events):
            span.add_event(f"event{i}", {"k": "v"})
        span.end()

    benchmark(benchmark_read_events)


@pytest.mark.parametrize("num_links", [1, 10, 50, 128])
def test_read_links(benchmark, num_links):
    provider = TracerProvider(sampler=sampling.DEFAULT_ON)
    provider.add_span_processor(_LinksReadingProcessor())
    t = provider.get_tracer("bench")

    def benchmark_read_links():
        span = t.start_span("benchmarkedSpan")
        for _ in range(num_links):
            span.add_link(_link_context)
        span.end()

    benchmark(benchmark_read_links)
