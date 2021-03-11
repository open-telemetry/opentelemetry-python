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

from re import compile as compile_
from re import search
from typing import Dict, Optional, Set

from opentelemetry.context.context import Context
from opentelemetry.propagators.textmap import TextMapPropagator
from opentelemetry.trace import (
    INVALID_SPAN,
    INVALID_SPAN_CONTEXT,
    NonRecordingSpan,
    SpanContext,
    TraceFlags,
    format_span_id,
    format_trace_id,
    get_current_span,
    set_span_in_context,
)
from opentelemetry.trace.span import TraceState


class TraceContextTextMapPropagator(TextMapPropagator):
    """Extracts and injects using w3c TraceContext's headers."""

    _traceparent_header_name = "traceparent"
    _tracestate_header_name = "tracestate"
    _traceparent_header_format_re = compile_(
        r"^\s*(?P<version>[0-9a-f]{2})-"
        r"(?P<trace_id>[0-9a-f]{32})-"
        r"(?P<span_id>[0-9a-f]{16})-"
        r"(?P<trace_flags>[0-9a-f]{2})"
        r"(?P<remainder>.+?)?\s*$"
    )

    def extract(
        self, carrier: Dict[str, str], context: Optional[Context] = None,
    ) -> Context:
        """Extracts SpanContext from the carrier.

        See `opentelemetry.propagators.textmap.TextMapPropagator.extract`
        """
        header = carrier.get(self._traceparent_header_name)

        if header is None:
            return set_span_in_context(INVALID_SPAN, context)

        match = search(self._traceparent_header_format_re, header)
        if match is None:
            return set_span_in_context(INVALID_SPAN, context)

        version = match.group("version")
        trace_id = match.group("trace_id")
        span_id = match.group("span_id")

        if (
            version == "ff"
            or trace_id == "0" * 32
            or span_id == "0" * 16
            or (version == "00" and match.group("remainder"))
        ):

            return set_span_in_context(INVALID_SPAN, context)

        tracestate_headers = carrier.get(self._tracestate_header_name)

        if tracestate_headers is None:
            tracestate = None
        else:
            tracestate = TraceState.from_header(tracestate_headers)

        return set_span_in_context(
            NonRecordingSpan(
                SpanContext(
                    trace_id=int(trace_id, 16),
                    span_id=int(span_id, 16),
                    is_remote=True,
                    trace_flags=TraceFlags(match.group("trace_flags")),
                    trace_state=tracestate,
                )
            ),
            context,
        )

    def inject(
        self, carrier: Dict[str, str], context: Optional[Context] = None,
    ) -> None:
        """Injects SpanContext into the carrier.

        See `opentelemetry.propagators.textmap.TextMapPropagator.inject`
        """
        span_context = get_current_span(context).get_span_context()
        if span_context == INVALID_SPAN_CONTEXT:
            return
        carrier[
            self._traceparent_header_name
        ] = "00-{trace_id}-{span_id}-{:02x}".format(
            span_context.trace_flags,
            trace_id=format_trace_id(span_context.trace_id),
            span_id=format_span_id(span_context.span_id),
        )

        if span_context.trace_state:
            carrier[
                self._tracestate_header_name
            ] = span_context.trace_state.to_header()

    @property
    def fields(self) -> Set[str]:
        """Returns a set with the fields set in `inject`.

        See
        `opentelemetry.propagators.textmap.TextMapPropagator.fields`
        """
        return {self._traceparent_header_name, self._tracestate_header_name}
