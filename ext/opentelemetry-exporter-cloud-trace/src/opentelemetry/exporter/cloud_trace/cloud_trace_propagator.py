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

_TRACE_CONTEXT_HEADER_NAME = "X-Cloud-Trace-Context"
_TRACE_CONTEXT_HEADER_FORMAT = r"(?P<trace_id>[0-9a-f]{32})\/(?P<span_id>[\d]{1,20});o=(?P<trace_flags>\d+)"
_TRACE_CONTEXT_HEADER_RE = re.compile(_TRACE_CONTEXT_HEADER_FORMAT)


class CloudTraceFormatPropagator(httptextformat.HTTPTextFormat):
    """This class is for injecting into a carrier the SpanContext in Google
    Cloud format, or extracting the SpanContext from a carrier using Google
    Cloud format.
    """

    def extract(
        self,
        get_from_carrier: httptextformat.Getter[
            httptextformat.HTTPTextFormatT
        ],
        carrier: httptextformat.HTTPTextFormatT,
        context: typing.Optional[Context] = None,
    ) -> Context:
        header = get_from_carrier(carrier, _TRACE_CONTEXT_HEADER_NAME)

        if not header:
            return trace.set_span_in_context(trace.INVALID_SPAN, context)

        match = re.fullmatch(_TRACE_CONTEXT_HEADER_RE, header[0])
        if match is None:
            return trace.set_span_in_context(trace.INVALID_SPAN, context)

        trace_id = match.group("trace_id")
        span_id = match.group("span_id")
        trace_options = match.group("trace_flags")

        if trace_id == "0" * 32 or int(span_id) == 0:
            return trace.set_span_in_context(trace.INVALID_SPAN, context)

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
        span_context = span.get_context()
        if span_context == trace.INVALID_SPAN_CONTEXT:
            return

        header = "{}/{};o={}".format(
            get_hexadecimal_trace_id(span_context.trace_id),
            span_context.span_id,
            int(span_context.trace_flags.sampled),
        )
        set_in_carrier(carrier, _TRACE_CONTEXT_HEADER_NAME, header)
