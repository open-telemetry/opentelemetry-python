# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pyright: reportIncompatibleMethodOverride=false, reportMissingTypeStubs=false
# pylint: disable=arguments-differ

"""Out-of-date API implementations keep working as the API grows.

The ``Frozen*`` classes stand in for implementations written against an older
API (vendor SDKs, custom tracers, test fakes). They take the API's positional
parameters but none of its optional keyword-only parameters, and no
``**kwargs``. Do NOT update them when the API changes: a failure here means an
API change breaks existing implementations.
"""

import contextlib
from collections.abc import Callable, Iterator, Sequence
from typing import Any

from opentelemetry import _logs, metrics, trace
from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.context import Context
from opentelemetry.metrics import (
    Counter,
    Histogram,
    NoOpCounter,
    NoOpHistogram,
    NoOpMeter,
)
from opentelemetry.test.globals_test import (
    LoggingGlobalsTest,
    MetricsGlobalsTest,
    TraceGlobalsTest,
)
from opentelemetry.util.types import Attributes


def _dynamic(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Hide ``fn``'s signature from type checkers to pass unknown keyword arguments."""
    return fn


class FrozenTracer(trace.NoOpTracer):
    def __init__(self) -> None:
        super().__init__()
        self.spans: list[tuple[str, trace.SpanKind, Attributes]] = []

    def start_span(
        self,
        name: str,
        context: Context | None = None,
        kind: trace.SpanKind = trace.SpanKind.INTERNAL,
        attributes: Attributes = None,
        links: Sequence[trace.Link] | None = None,
        start_time: int | None = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
    ) -> trace.Span:
        self.spans.append((name, kind, attributes))
        return trace.INVALID_SPAN

    @contextlib.contextmanager
    def start_as_current_span(
        self,
        name: str,
        context: Context | None = None,
        kind: trace.SpanKind = trace.SpanKind.INTERNAL,
        attributes: Attributes = None,
        links: Sequence[trace.Link] | None = None,
        start_time: int | None = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
        end_on_exit: bool = True,
    ) -> Iterator[trace.Span]:
        self.spans.append((name, kind, attributes))
        yield trace.INVALID_SPAN


class FrozenTracerProvider(trace.TracerProvider):
    def __init__(self) -> None:
        self.tracer = FrozenTracer()

    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str | None = None,
        schema_url: str | None = None,
        attributes: Attributes = None,
    ) -> trace.Tracer:
        return self.tracer


class FrozenMeter(NoOpMeter):
    def __init__(self) -> None:
        super().__init__("frozen")
        self.counters: list[tuple[str, str, str]] = []
        self.histograms: list[tuple[str, str, str]] = []

    def create_counter(self, name: str, unit: str = "", description: str = "") -> Counter:
        self.counters.append((name, unit, description))
        return NoOpCounter(name, unit, description)

    def create_histogram(self, name: str, unit: str = "", description: str = "") -> Histogram:
        self.histograms.append((name, unit, description))
        return NoOpHistogram(name, unit, description)


class FrozenMeterProvider(metrics.MeterProvider):
    def __init__(self) -> None:
        self.meter = FrozenMeter()

    def get_meter(
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: Attributes = None,
    ) -> metrics.Meter:
        return self.meter


class FrozenLogger(_logs.Logger):
    def __init__(self) -> None:
        super().__init__("frozen")
        self.records: list[LogRecord | None] = []

    def emit(self, record: LogRecord | None = None) -> None:
        self.records.append(record)

    def enabled(self) -> bool:
        return True


class FrozenLoggerProvider(_logs.LoggerProvider):
    def __init__(self) -> None:
        self.logger = FrozenLogger()

    def get_logger(
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: Attributes = None,
    ) -> _logs.Logger:
        return self.logger


class TestFrozenTracer(TraceGlobalsTest):
    def test_start_span(self) -> None:
        tracer = trace.get_tracer("my.library")
        provider = FrozenTracerProvider()
        trace.set_tracer_provider(provider)

        span = tracer.start_span("GET /users", kind=trace.SpanKind.SERVER, attributes={"http.method": "GET"})
        # A keyword argument that no version of the API has defined
        _dynamic(tracer.start_span)("GET /items", not_yet_invented=True)

        self.assertIs(span, trace.INVALID_SPAN)
        self.assertEqual(
            provider.tracer.spans,
            [
                ("GET /users", trace.SpanKind.SERVER, {"http.method": "GET"}),
                ("GET /items", trace.SpanKind.INTERNAL, None),
            ],
        )

    def test_start_as_current_span(self) -> None:
        tracer = trace.get_tracer("my.library")
        provider = FrozenTracerProvider()
        trace.set_tracer_provider(provider)

        with _dynamic(tracer.start_as_current_span)("work", kind=trace.SpanKind.CLIENT, not_yet_invented=True) as span:
            self.assertIs(span, trace.INVALID_SPAN)

        self.assertEqual(provider.tracer.spans, [("work", trace.SpanKind.CLIENT, None)])


class TestFrozenMeter(MetricsGlobalsTest):
    def test_instruments_created_before_provider_is_set(self) -> None:
        # The proxy meter re-creates these on the real meter once it is set,
        # passing explicit_bucket_boundaries_advisory which FrozenMeter predates.
        meter = metrics.get_meter("my.library")
        meter.create_counter("requests", unit="1", description="Requests served")
        meter.create_histogram("duration", unit="ms", explicit_bucket_boundaries_advisory=[5.0, 10.0, 25.0])
        provider = FrozenMeterProvider()
        metrics.set_meter_provider(provider)

        self.assertEqual(provider.meter.counters, [("requests", "1", "Requests served")])
        self.assertEqual(provider.meter.histograms, [("duration", "ms", "")])

    def test_unknown_keyword_argument(self) -> None:
        provider = FrozenMeterProvider()
        metrics.set_meter_provider(provider)
        meter = metrics.get_meter("my.library")

        # A keyword argument that no version of the API has defined
        _dynamic(meter.create_counter)("requests", not_yet_invented=True)

        self.assertEqual(provider.meter.counters, [("requests", "", "")])


class TestFrozenLogger(LoggingGlobalsTest):
    def test_emit_and_enabled(self) -> None:
        logger = _logs.get_logger("my.library")
        provider = FrozenLoggerProvider()
        _logs.set_logger_provider(provider)

        self.assertTrue(logger.enabled(severity_number=SeverityNumber.WARN, event_name="disk.full"))
        record = LogRecord(body="disk full", severity_number=SeverityNumber.WARN)
        logger.emit(record)
        # Keyword-only fields FrozenLogger predates are dropped, but the call still reaches it
        logger.emit(body="disk full", severity_number=SeverityNumber.WARN, exception=OSError("disk full"))

        self.assertEqual(provider.logger.records, [record, None])
