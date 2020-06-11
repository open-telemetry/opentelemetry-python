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
#

import re
import typing

import opentelemetry.trace as trace
from opentelemetry.context.context import Context
from opentelemetry.trace.propagation import httptextformat
from opentelemetry.trace.span import (
    SpanContext,
    TraceFlags,
    get_hexadecimal_trace_id,
)

_TRACE_ID_DELIMETER = "/"
_SPAN_ID_DELIMETER = ";"


class GoogleCloudFormatPropagator(httptextformat.HTTPTextFormat):
    """This class is for converting the trace header in google cloud format
    and generate a SpanContext, or converting a SpanContext to a google cloud
    format header. Later we will add implementation for supporting other
    format like binary format and zipkin, opencensus format.
    """

    _TRACE_CONTEXT_HEADER_NAME = "X-Cloud-Trace-Context"
    _TRACE_CONTEXT_HEADER_FORMAT = (
        r"([0-9a-f]{32})(\/([\d]{0,20}))?(;o=(\d+))?"
    )
    _TRACE_CONTEXT_HEADER_RE = re.compile(_TRACE_CONTEXT_HEADER_FORMAT)

    def extract(
        self,
        get_from_carrier: httptextformat.Getter[
            httptextformat.HTTPTextFormatT
        ],
        carrier: httptextformat.HTTPTextFormatT,
        context: typing.Optional[Context] = None,
    ) -> Context:
        """Extract CorrelationContext from the carrier.

        See
        `opentelemetry.trace.propagation.httptextformat.HTTPTextFormat.extract`
        """
        header = get_from_carrier(carrier, self._TRACE_CONTEXT_HEADER_NAME)

        if not header:
            return trace.set_span_in_context(trace.INVALID_SPAN, context)

        match = re.search(self._TRACE_CONTEXT_HEADER_RE, header[0])
        if not match:
            return trace.set_span_in_context(trace.INVALID_SPAN, context)

        trace_id = match.group(1)
        span_id = match.group(3)
        trace_options = match.group(5)

        if trace_id == "0" * 32 or span_id == "0" * 16:
            return trace.set_span_in_context(trace.INVALID_SPAN, context)

        if trace_options is None:
            trace_options = 1

        span_context = SpanContext(
            trace_id=int(trace_id, 16),
            span_id=int(span_id),
            is_remote=True,
            trace_flags=TraceFlags(trace_options),
        )
        return trace.set_span_in_context(
            trace.DefaultSpan(span_context), context
        )

    def inject(
        self,
        set_in_carrier: httptextformat.Setter[httptextformat.HTTPTextFormatT],
        carrier: httptextformat.HTTPTextFormatT,
        context: typing.Optional[Context] = None,
    ) -> None:
        span = trace.get_current_span(context)
        if span is None:
            return
        span_context = span.get_context()
        if span_context == trace.INVALID_SPAN_CONTEXT:
            return

        header = "{}/{};o={}".format(
            get_hexadecimal_trace_id(span_context.trace_id),
            span_context.span_id,
            int(span_context.trace_flags),
        )

        set_in_carrier(carrier, self._TRACE_CONTEXT_HEADER_NAME, header)
