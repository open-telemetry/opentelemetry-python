# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import collections.abc
import itertools
import urllib.parse

from opentelemetry import baggage, trace
from opentelemetry.context import Context
from opentelemetry.propagators.textmap import (
    CarrierT,
    Getter,
    Setter,
    TextMapPropagator,
    default_getter,
    default_setter,
)
from opentelemetry.trace import SpanContext, format_span_id, format_trace_id


class JaegerPropagator(TextMapPropagator):
    """Propagator for the Jaeger format.

    See: https://www.jaegertracing.io/docs/1.19/client-libraries/#propagation-format
    """

    TRACE_ID_KEY = "uber-trace-id"
    BAGGAGE_PREFIX = "uberctx-"
    DEBUG_FLAG = 0x02
    # The Jaeger format defines no baggage limits, so the W3C Baggage spec
    # limits are borrowed to bound an unbounded inbound carrier on extract.
    MAX_BAGGAGE_ENTRIES = 180
    MAX_BAGGAGE_ENTRY_BYTES = 4096
    MAX_BAGGAGE_TOTAL_BYTES = 8192

    def extract(
        self,
        carrier: CarrierT,
        context: Context | None = None,
        getter: Getter[CarrierT] = default_getter,
    ) -> Context:
        if context is None:
            context = Context()
        header = getter.get(carrier, self.TRACE_ID_KEY)
        if not header:
            return context

        context = self._extract_baggage(getter, carrier, context)

        trace_id, span_id, flags = _parse_trace_id_header(header)
        if trace_id == trace.INVALID_TRACE_ID or span_id == trace.INVALID_SPAN_ID:
            return context

        span = trace.NonRecordingSpan(
            trace.SpanContext(
                trace_id=trace_id,
                span_id=span_id,
                is_remote=True,
                trace_flags=trace.TraceFlags(flags & trace.TraceFlags.SAMPLED),
            )
        )
        return trace.set_span_in_context(span, context)

    def inject(
        self,
        carrier: CarrierT,
        context: Context | None = None,
        setter: Setter[CarrierT] = default_setter,
    ) -> None:
        span = trace.get_current_span(context=context)
        span_context = span.get_span_context()
        if span_context == trace.INVALID_SPAN_CONTEXT:
            return

        # Non-recording spans do not have a parent; the API Span type does not
        # declare a parent attribute, so it has to be accessed via getattr
        parent: SpanContext | None = getattr(span, "parent", None) if span.is_recording() else None
        span_parent_id = parent.span_id if parent else 0
        trace_flags = span_context.trace_flags
        if trace_flags.sampled:
            trace_flags |= self.DEBUG_FLAG

        # set span identity
        setter.set(
            carrier,
            self.TRACE_ID_KEY,
            _format_uber_trace_id(
                span_context.trace_id,
                span_context.span_id,
                span_parent_id,
                trace_flags,
            ),
        )

        # set span baggage, if any
        baggage_entries = baggage.get_all(context=context)
        if not baggage_entries:
            return
        self._inject_baggage(setter, carrier, baggage_entries)

    @property
    def fields(self) -> set[str]:
        return {self.TRACE_ID_KEY}

    def _extract_baggage(
        self,
        getter: Getter[CarrierT],
        carrier: CarrierT,
        context: Context,
    ) -> Context:
        # The limit bounds the candidates inspected, not the entries kept, so a
        # carrier full of oversized ones cannot force unbounded work.
        candidates = itertools.islice(
            (key for key in getter.keys(carrier) if key.startswith(self.BAGGAGE_PREFIX)),
            self.MAX_BAGGAGE_ENTRIES,
        )
        pairs = []
        for key in candidates:
            value = _extract_first_element(getter.get(carrier, key))
            if value is not None:
                pairs.append((key.replace(self.BAGGAGE_PREFIX, ""), value))

        for baggage_key, value in _limit_baggage_bytes(
            pairs, self.MAX_BAGGAGE_ENTRY_BYTES, self.MAX_BAGGAGE_TOTAL_BYTES
        ):
            context = baggage.set_baggage(
                baggage_key,
                urllib.parse.unquote(value).strip(),
                context=context,
            )
        return context

    def _inject_baggage(
        self,
        setter: Setter[CarrierT],
        carrier: CarrierT,
        baggage_entries: collections.abc.Mapping[str, object],
    ) -> None:
        candidates = itertools.islice(baggage_entries.items(), self.MAX_BAGGAGE_ENTRIES)
        pairs = [(key, urllib.parse.quote(str(value))) for key, value in candidates]

        for key, encoded_value in _limit_baggage_bytes(
            pairs, self.MAX_BAGGAGE_ENTRY_BYTES, self.MAX_BAGGAGE_TOTAL_BYTES
        ):
            setter.set(carrier, self.BAGGAGE_PREFIX + key, encoded_value)


def _limit_baggage_bytes(
    pairs: collections.abc.Iterable[tuple[str, str]],
    max_entry_bytes: int,
    max_total_bytes: int,
) -> collections.abc.Iterator[tuple[str, str]]:
    total_bytes = 0
    accepted = 0
    for key, value in pairs:
        entry_bytes = len(key.encode()) + len(value.encode()) + 1
        if entry_bytes > max_entry_bytes:
            continue
        separator_bytes = 1 if accepted > 0 else 0
        if total_bytes + separator_bytes + entry_bytes > max_total_bytes:
            continue
        yield key, value
        total_bytes += separator_bytes + entry_bytes
        accepted += 1


def _format_uber_trace_id(trace_id, span_id, parent_span_id, flags):
    return f"{format_trace_id(trace_id)}:{format_span_id(span_id)}:{format_span_id(parent_span_id)}:{flags:02x}"


def _extract_first_element(
    items: collections.abc.Iterable[str] | None,
) -> str | None:
    if items is None:
        return None
    return next(iter(items), None)


def _parse_trace_id_header(
    items: collections.abc.Iterable[str],
) -> tuple[int, int, int]:
    invalid_header_result = (trace.INVALID_TRACE_ID, trace.INVALID_SPAN_ID, 0)

    header = _extract_first_element(items)
    if header is None:
        return invalid_header_result

    fields = header.split(":")
    if len(fields) != 4:
        return invalid_header_result

    trace_id_str, span_id_str, _parent_id_str, flags_str = fields
    flags = _int_from_hex_str(flags_str)
    if flags is None:
        return invalid_header_result

    trace_id = _int_from_hex_str(trace_id_str)
    if trace_id is None:
        trace_id = trace.INVALID_TRACE_ID
    span_id = _int_from_hex_str(span_id_str)
    if span_id is None:
        span_id = trace.INVALID_SPAN_ID
    return trace_id, span_id, flags


def _int_from_hex_str(identifier: str) -> int | None:
    try:
        return int(identifier, 16)
    except ValueError:
        return None
