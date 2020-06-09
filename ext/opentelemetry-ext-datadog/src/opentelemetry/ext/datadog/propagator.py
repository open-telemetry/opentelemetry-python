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

import typing

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace import get_current_span, set_span_in_context
from opentelemetry.trace.propagation.httptextformat import (
    Getter,
    HTTPTextFormat,
    HTTPTextFormatT,
    Setter,
)

# pylint:disable=relative-beyond-top-level
from . import constants


class DatadogFormat(HTTPTextFormat):
    """Propagator for the Datadog HTTP header format.
    """

    TRACE_ID_KEY = "x-datadog-trace-id"
    PARENT_ID_KEY = "x-datadog-parent-id"
    SAMPLING_PRIORITY_KEY = "x-datadog-sampling-priority"
    ORIGIN_KEY = "x-datadog-origin"

    def extract(
        self,
        get_from_carrier: Getter[HTTPTextFormatT],
        carrier: HTTPTextFormatT,
        context: typing.Optional[Context] = None,
    ) -> Context:
        trace_id = extract_first_element(
            get_from_carrier(carrier, self.TRACE_ID_KEY)
        )

        span_id = extract_first_element(
            get_from_carrier(carrier, self.PARENT_ID_KEY)
        )

        sampled = extract_first_element(
            get_from_carrier(carrier, self.SAMPLING_PRIORITY_KEY)
        )

        origin = extract_first_element(
            get_from_carrier(carrier, self.ORIGIN_KEY)
        )

        trace_flags = trace.TraceFlags()
        if sampled and int(sampled) in (
            constants.AUTO_KEEP,
            constants.USER_KEEP,
        ):
            trace_flags |= trace.TraceFlags.SAMPLED

        if trace_id is None or span_id is None:
            return set_span_in_context(trace.INVALID_SPAN, context)

        span_context = trace.SpanContext(
            trace_id=int(trace_id),
            span_id=int(span_id),
            is_remote=True,
            trace_flags=trace_flags,
            trace_state=trace.TraceState({constants.DD_ORIGIN: origin}),
        )

        return set_span_in_context(trace.DefaultSpan(span_context), context)

    def inject(
        self,
        set_in_carrier: Setter[HTTPTextFormatT],
        carrier: HTTPTextFormatT,
        context: typing.Optional[Context] = None,
    ) -> None:
        span = get_current_span(context)
        sampled = (trace.TraceFlags.SAMPLED & span.context.trace_flags) != 0
        set_in_carrier(
            carrier, self.TRACE_ID_KEY, format_trace_id(span.context.trace_id),
        )
        set_in_carrier(
            carrier, self.PARENT_ID_KEY, format_span_id(span.context.span_id)
        )
        set_in_carrier(
            carrier,
            self.SAMPLING_PRIORITY_KEY,
            str(constants.AUTO_KEEP if sampled else constants.AUTO_REJECT),
        )
        if constants.DD_ORIGIN in span.context.trace_state:
            set_in_carrier(
                carrier,
                self.ORIGIN_KEY,
                span.context.trace_state[constants.DD_ORIGIN],
            )


def format_trace_id(trace_id: int) -> str:
    """Format the trace id for Datadog."""
    return str(trace_id & 0xFFFFFFFFFFFFFFFF)


def format_span_id(span_id: int) -> str:
    """Format the span id for Datadog."""
    return str(span_id)


def extract_first_element(
    items: typing.Iterable[HTTPTextFormatT],
) -> typing.Optional[HTTPTextFormatT]:
    if items is None:
        return None
    return next(iter(items), None)
