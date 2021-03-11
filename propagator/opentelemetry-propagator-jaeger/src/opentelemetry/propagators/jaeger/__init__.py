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

from typing import Dict, Optional, Set
from urllib.parse import quote, unquote

from opentelemetry import baggage
from opentelemetry.context import Context, get_current
from opentelemetry.propagators.textmap import TextMapPropagator
from opentelemetry.trace import (
    INVALID_SPAN,
    INVALID_SPAN_CONTEXT,
    INVALID_SPAN_ID,
    INVALID_TRACE_ID,
    NonRecordingSpan,
    SpanContext,
    TraceFlags,
    format_span_id,
    format_trace_id,
    get_current_span,
    set_span_in_context,
)


class JaegerPropagator(TextMapPropagator):
    """Propagator for the Jaeger format.

    See: https://www.jaegertracing.io/docs/1.19/client-libraries/#propagation-format
    """

    _trace_id_key = "uber-trace-id"
    _baggage_prefix = "uberctx-"
    _debug_flag = 0x02

    def extract(
        self, carrier: Dict[str, str], context: Optional[Context] = None,
    ) -> Context:

        if context is None:
            context = get_current()
        header = carrier.get(self._trace_id_key)
        if header is None:
            return set_span_in_context(INVALID_SPAN, context)
        fields = header.split(":")

        for key in [
            key
            for key in carrier.keys()
            if key.startswith(self._baggage_prefix)
        ]:
            context = baggage.set_baggage(
                key.replace(self._baggage_prefix, ""),
                unquote(carrier[key]).strip(),
                context=context,
            )

        if len(fields) != 4:
            return set_span_in_context(INVALID_SPAN, context)

        trace_id, span_id, _parent_id, flags = fields
        if trace_id == INVALID_TRACE_ID or span_id == INVALID_SPAN_ID:
            return set_span_in_context(INVALID_SPAN, context)

        span = NonRecordingSpan(
            SpanContext(
                trace_id=int(trace_id, 16),
                span_id=int(span_id, 16),
                is_remote=True,
                trace_flags=TraceFlags(int(flags, 16) & TraceFlags.SAMPLED),
            )
        )
        return set_span_in_context(span, context)

    def inject(
        self, carrier: Dict[str, str], context: Optional[Context] = None,
    ) -> None:
        span = get_current_span(context=context)
        span_context = span.get_span_context()
        if span_context == INVALID_SPAN_CONTEXT:
            return

        span_parent_id = span.parent.span_id if span.parent else 0
        trace_flags = span_context.trace_flags
        if trace_flags.sampled:
            trace_flags |= self._debug_flag

        # set span identity
        carrier[self._trace_id_key] = _format_uber_trace_id(
            span_context.trace_id,
            span_context.span_id,
            span_parent_id,
            trace_flags,
        )

        # set span baggage, if any
        baggage_entries = baggage.get_all(context=context)
        if not baggage_entries:
            return
        for key, value in baggage_entries.items():
            baggage_key = self._baggage_prefix + key
            carrier[baggage_key] = quote(str(value))

    @property
    def fields(self) -> Set[str]:
        return {self._trace_id_key}


def _format_uber_trace_id(trace_id, span_id, parent_span_id, flags):
    return "{trace_id}:{span_id}:{parent_id}:{flags:02x}".format(
        trace_id=format_trace_id(trace_id),
        span_id=format_span_id(span_id),
        parent_id=format_span_id(parent_span_id),
        flags=flags,
    )
