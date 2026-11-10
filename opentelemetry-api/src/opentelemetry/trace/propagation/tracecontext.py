# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
#
"""Serialization of a span context into the W3C trace context headers.

:class:`TraceContextTextMapPropagator` writes the ``traceparent`` and
``tracestate`` headers when a request is sent and reads them back when one is
received, following https://www.w3.org/TR/trace-context/. This is the format
that makes a trace continue across a service boundary.
"""

import logging
import re

from opentelemetry import trace
from opentelemetry.context.context import Context
from opentelemetry.propagators import textmap
from opentelemetry.trace import format_span_id, format_trace_id
from opentelemetry.trace.span import (
    _TRACECONTEXT_MAXIMUM_TRACESTATE_LENGTH,
    TraceState,
)

_logger = logging.getLogger(__name__)


class TraceContextTextMapPropagator(textmap.TextMapPropagator):
    """Extracts and injects using w3c TraceContext's headers."""

    _TRACEPARENT_HEADER_NAME = "traceparent"
    _TRACESTATE_HEADER_NAME = "tracestate"
    _TRACEPARENT_HEADER_FORMAT = (
        "^[ \t]*([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})" + "(?:(-.*)|[ \t]*)$"
    )
    _TRACEPARENT_HEADER_FORMAT_RE = re.compile(_TRACEPARENT_HEADER_FORMAT)
    _TRACEPARENT_MAXIMUM_LENGTH = 512

    # pylint: disable-next=too-many-return-statements
    def extract(
        self,
        carrier: textmap.CarrierT,
        context: Context | None = None,
        getter: textmap.Getter[textmap.CarrierT] = textmap.default_getter,
    ) -> Context:
        """Extracts SpanContext from the carrier.

        See `opentelemetry.propagators.textmap.TextMapPropagator.extract`

        A ``traceparent`` header that is absent, too long, malformed, carries
        an all-zero trace or span id, or names version ``ff`` is ignored and
        the context is returned unchanged. A ``tracestate`` header that
        exceeds the maximum length is dropped while the ``traceparent`` is
        still honoured.

        Args:
            carrier: The object holding the incoming headers.
            context: The context to add the extracted span to. If ``None``, an
                empty context is used rather than the current one.
            getter: Reads the header values out of ``carrier``.

        Returns:
            A context holding a
            :class:`~opentelemetry.trace.NonRecordingSpan` built from the
            headers, marked as remote. The context is returned unchanged when
            no valid ``traceparent`` is present.
        """
        if context is None:
            context = Context()

        header = getter.get(carrier, self._TRACEPARENT_HEADER_NAME)

        if not header:
            return context

        if len(header[0]) > self._TRACEPARENT_MAXIMUM_LENGTH:
            _logger.warning(
                "traceparent header exceeded the maximum length of %d characters",
                self._TRACEPARENT_MAXIMUM_LENGTH,
            )
            return context

        match = re.search(self._TRACEPARENT_HEADER_FORMAT_RE, header[0])
        if not match:
            return context

        version: str = match.group(1)
        trace_id: str = match.group(2)
        span_id: str = match.group(3)
        trace_flags: str = match.group(4)

        if trace_id == "0" * 32 or span_id == "0" * 16:
            return context

        if version == "00":
            if match.group(5):  # type: ignore
                return context
        if version == "ff":
            return context

        tracestate_headers = getter.get(carrier, self._TRACESTATE_HEADER_NAME)
        if tracestate_headers is None:
            tracestate = None
        elif (
            # multiple header fields are combined with "," (RFC 9110, section 5.3)
            sum(len(header) for header in tracestate_headers) + len(tracestate_headers) - 1
            > _TRACECONTEXT_MAXIMUM_TRACESTATE_LENGTH
        ):
            _logger.warning(
                "tracestate header exceeded the maximum length of %d characters",
                _TRACECONTEXT_MAXIMUM_TRACESTATE_LENGTH,
            )
            tracestate = None
        else:
            tracestate = TraceState.from_header(tracestate_headers)

        span_context = trace.SpanContext(
            trace_id=int(trace_id, 16),
            span_id=int(span_id, 16),
            is_remote=True,
            trace_flags=trace.TraceFlags(int(trace_flags, 16)),
            trace_state=tracestate,
        )
        return trace.set_span_in_context(trace.NonRecordingSpan(span_context), context)

    def inject(
        self,
        carrier: textmap.CarrierT,
        context: Context | None = None,
        setter: textmap.Setter[textmap.CarrierT] = textmap.default_setter,
    ) -> None:
        """Injects SpanContext into the carrier.

        See `opentelemetry.propagators.textmap.TextMapPropagator.inject`

        Nothing is written when the current span context is invalid, so a
        request made outside any span carries no trace context header. The
        ``tracestate`` header is written only when the span context carries a
        non-empty trace state.

        Args:
            carrier: The object to write the outgoing headers into.
            context: The context to read the current span from. If ``None``,
                the current context is used.
            setter: Writes the headers into ``carrier``.
        """
        span = trace.get_current_span(context)
        span_context = span.get_span_context()
        if not span_context.is_valid:
            return
        traceparent_string = f"00-{format_trace_id(span_context.trace_id)}-{format_span_id(span_context.span_id)}-{span_context.trace_flags:02x}"
        setter.set(carrier, self._TRACEPARENT_HEADER_NAME, traceparent_string)
        if span_context.trace_state:
            tracestate_string = span_context.trace_state.to_header()
            setter.set(carrier, self._TRACESTATE_HEADER_NAME, tracestate_string)

    @property
    def fields(self) -> set[str]:
        """Returns a set with the fields set in `inject`.

        See
        `opentelemetry.propagators.textmap.TextMapPropagator.fields`

        Returns:
            A set holding ``"traceparent"`` and ``"tracestate"``. A caller
            clearing a carrier before injecting into it should remove these
            names.
        """
        return {self._TRACEPARENT_HEADER_NAME, self._TRACESTATE_HEADER_NAME}
