# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=protected-access

# Tracer implementations written against the current API, the way third parties
# write them. They must keep working, and keep type-checking, when the API grows.

from collections.abc import Iterator
from typing import Any

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.test.globals_test import TraceGlobalsTest
from opentelemetry.trace import (
    INVALID_SPAN,
    NoOpTracer,
    NoOpTracerProvider,
    Span,
    SpanKind,
    Tracer,
    _Links,
)
from opentelemetry.util import types
from opentelemetry.util._decorator import _agnosticcontextmanager


class ExplicitTracer(Tracer):
    """Overrides both methods with the full signature, no **kwargs."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def start_span(
        self,
        name: str,
        context: Context | None = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: _Links = None,
        start_time: int | None = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
    ) -> Span:
        self.calls.append(("start_span", {"name": name, "kind": kind, "attributes": attributes}))
        return INVALID_SPAN

    @_agnosticcontextmanager
    def start_as_current_span(
        self,
        name: str,
        context: Context | None = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: _Links = None,
        start_time: int | None = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
        end_on_exit: bool = True,
    ) -> Iterator[Span]:
        self.calls.append(("start_as_current_span", {"name": name, "kind": kind, "attributes": attributes}))
        yield INVALID_SPAN


class ShortSignatureTracer(Tracer):
    """Overrides with a subset of parameters, as minimal implementations do."""

    def start_span(  # type: ignore[override]  # pylint: disable=arguments-differ
        self, name: str, context: Context | None = None, kind: SpanKind = SpanKind.INTERNAL
    ) -> Span:
        return INVALID_SPAN

    @_agnosticcontextmanager
    def start_as_current_span(  # type: ignore[override]  # pylint: disable=arguments-differ
        self, name: str, context: Context | None = None, kind: SpanKind = SpanKind.INTERNAL
    ) -> Iterator[Span]:
        yield INVALID_SPAN


class DelegatingTracer(NoOpTracer):
    """Wraps another tracer and forwards positionally via super()."""

    def __init__(self) -> None:
        self.started: list[str] = []

    def start_span(
        self,
        name: str,
        context: Context | None = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: _Links = None,
        start_time: int | None = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
    ) -> Span:
        self.started.append(name)
        return super().start_span(
            name,
            context,
            kind,
            attributes,
            links,
            start_time,
            record_exception,
            set_status_on_exception,
        )


class _Provider(NoOpTracerProvider):
    def __init__(self, tracer: Tracer) -> None:
        self._tracer = tracer

    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str | None = None,
        schema_url: str | None = None,
        attributes: types.Attributes = None,
    ) -> Tracer:
        return self._tracer


class TestLegacyTracerImplementations(TraceGlobalsTest):
    def test_explicit_tracer_direct(self):
        tracer = ExplicitTracer()
        tracer.start_span("a", None, SpanKind.CLIENT, {"k": "v"})
        with tracer.start_as_current_span("b", kind=SpanKind.SERVER):
            pass

        @tracer.start_as_current_span("c")
        def decorated() -> int:
            return 1

        self.assertEqual(decorated(), 1)
        self.assertEqual(
            tracer.calls,
            [
                ("start_span", {"name": "a", "kind": SpanKind.CLIENT, "attributes": {"k": "v"}}),
                ("start_as_current_span", {"name": "b", "kind": SpanKind.SERVER, "attributes": None}),
                ("start_as_current_span", {"name": "c", "kind": SpanKind.INTERNAL, "attributes": None}),
            ],
        )

    def test_explicit_tracer_through_proxy(self):
        proxy = trace.get_tracer("instr")
        tracer = ExplicitTracer()
        trace.set_tracer_provider(_Provider(tracer))

        proxy.start_span("a", kind=SpanKind.CLIENT)
        with proxy.start_as_current_span("b"):
            pass

        self.assertEqual([c[1]["name"] for c in tracer.calls], ["a", "b"])

    def test_short_signature_tracer(self):
        trace.set_tracer_provider(_Provider(ShortSignatureTracer()))
        tracer = trace.get_tracer("instr")
        self.assertIs(tracer.start_span("a", kind=SpanKind.CLIENT), INVALID_SPAN)
        with tracer.start_as_current_span("b") as span:
            self.assertIs(span, INVALID_SPAN)

    def test_typed_span_with_short_signature_tracer(self):
        trace.set_tracer_provider(_Provider(ShortSignatureTracer()))
        tracer = trace.get_tracer("instr")
        span = tracer._start_typed_span("a", kind=SpanKind.CLIENT, span_type="http.client.request")
        self.assertIs(span, INVALID_SPAN)
        with tracer._start_as_current_typed_span("b", span_type="http.client.request") as span:
            self.assertIs(span, INVALID_SPAN)

    def test_delegating_tracer(self):
        tracer = DelegatingTracer()
        tracer.start_span("a", None, SpanKind.CLIENT)
        with tracer.start_as_current_span("b"):
            pass
        self.assertEqual(tracer.started, ["a", "b"])

    def test_typed_span_with_explicit_tracer(self):
        explicit = ExplicitTracer()
        trace.set_tracer_provider(_Provider(explicit))
        tracer = trace.get_tracer("instr")
        tracer._start_typed_span("a", kind=SpanKind.CLIENT, attributes={"k": "v"}, span_type="http.client.request")
        with tracer._start_as_current_typed_span("b", span_type="http.client.request", future_arg=1):
            pass
        tracer._start_typed_span("c", record_exception=False)

        self.assertEqual(
            explicit.calls,
            [
                ("start_span", {"name": "a", "kind": SpanKind.CLIENT, "attributes": {"k": "v"}}),
                ("start_as_current_span", {"name": "b", "kind": SpanKind.INTERNAL, "attributes": None}),
                ("start_span", {"name": "c", "kind": SpanKind.INTERNAL, "attributes": None}),
            ],
        )

    def test_typed_span_with_delegating_tracer(self):
        tracer = DelegatingTracer()
        tracer._start_typed_span("a", span_type="http.client.request")
        with tracer._start_as_current_typed_span("b", span_type="http.client.request"):
            pass
        self.assertEqual(tracer.started, ["a", "b"])

    def test_typed_span_with_noop_tracer(self):
        with trace.get_tracer("instr")._start_as_current_typed_span("a", span_type="not valid!") as span:
            self.assertFalse(span.is_recording())

    def test_typed_span_through_proxy_created_before_provider(self):
        proxy = trace.get_tracer("instr")
        self.assertIsInstance(proxy, trace.ProxyTracer)
        explicit = ExplicitTracer()
        trace.set_tracer_provider(_Provider(explicit))

        proxy._start_typed_span("a", span_type="http.client.request", kind=SpanKind.CLIENT)
        with proxy._start_as_current_typed_span("b", span_type="http.client.request"):
            pass

        self.assertEqual(
            explicit.calls,
            [
                ("start_span", {"name": "a", "kind": SpanKind.CLIENT, "attributes": None}),
                ("start_as_current_span", {"name": "b", "kind": SpanKind.INTERNAL, "attributes": None}),
            ],
        )
