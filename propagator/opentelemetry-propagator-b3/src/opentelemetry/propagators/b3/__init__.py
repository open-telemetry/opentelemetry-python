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
from typing import Dict, Optional, Set

import opentelemetry.trace as trace
from opentelemetry.context import Context
from opentelemetry.propagators.textmap import TextMapPropagator
from opentelemetry.trace import format_span_id, format_trace_id


class B3Format(TextMapPropagator):
    """Propagator for the B3 HTTP header format.

    See: https://github.com/openzipkin/b3-propagation
    """

    SINGLE_HEADER_KEY = "b3"
    TRACE_ID_KEY = "x-b3-traceid"
    SPAN_ID_KEY = "x-b3-spanid"
    PARENT_SPAN_ID_KEY = "x-b3-parentspanid"
    SAMPLED_KEY = "x-b3-sampled"
    FLAGS_KEY = "x-b3-flags"
    _SAMPLE_PROPAGATE_VALUES = set(["1", "True", "true", "d"])
    _trace_id_regex = compile_(r"[\da-fA-F]{16}|[\da-fA-F]{32}")
    _span_id_regex = compile_(r"[\da-fA-F]{16}")

    def extract(
        self, carrier: Dict[str, str], context: Optional[Context] = None,
    ) -> Context:

        trace_id = format_trace_id(trace.INVALID_TRACE_ID)
        span_id = format_span_id(trace.INVALID_SPAN_ID)
        sampled = "0"
        flags = None

        single_header = carrier.get(self.SINGLE_HEADER_KEY)

        if single_header is not None:
            # The b3 spec calls for the sampling state to be
            # "deferred", which is unspecified. This concept does not
            # translate to SpanContext, so we set it as recorded.
            sampled = "1"
            fields = single_header.split("-", 4)

            if len(fields) == 1:
                sampled = fields[0]
            elif len(fields) == 2:
                trace_id, span_id = fields
            elif len(fields) == 3:
                trace_id, span_id, sampled = fields
            elif len(fields) == 4:
                trace_id, span_id, sampled, _ = fields
            else:
                return trace.set_span_in_context(trace.INVALID_SPAN)
        else:
            trace_id = carrier.get(self.TRACE_ID_KEY, False) or trace_id
            span_id = carrier.get(self.SPAN_ID_KEY, False) or span_id
            sampled = carrier.get(self.SAMPLED_KEY, False) or sampled
            flags = carrier.get(self.FLAGS_KEY, False) or flags

        if (
            self._trace_id_regex.fullmatch(trace_id) is None
            or self._span_id_regex.fullmatch(span_id) is None
        ):
            id_generator = trace.get_tracer_provider().id_generator
            trace_id = id_generator.generate_trace_id()
            span_id = id_generator.generate_span_id()
            sampled = "0"

        else:
            trace_id = int(trace_id, 16)
            span_id = int(span_id, 16)

        options = 0
        # The b3 spec provides no defined behavior for both sample and
        # flag values set. Since the setting of at least one implies
        # the desire for some form of sampling, propagate if either
        # header is set to allow.
        if sampled in self._SAMPLE_PROPAGATE_VALUES or flags == "1":
            options |= trace.TraceFlags.SAMPLED

        return trace.set_span_in_context(
            trace.NonRecordingSpan(
                trace.SpanContext(
                    # trace an span ids are encoded in hex, so must be converted
                    trace_id=trace_id,
                    span_id=span_id,
                    is_remote=True,
                    trace_flags=trace.TraceFlags(options),
                    trace_state=trace.TraceState(),
                )
            )
        )

    def inject(
        self, carrier: Dict[str, str], context: Optional[Context] = None,
    ) -> None:

        span = trace.get_current_span(context=context)

        span_context = span.get_span_context()
        if span_context == trace.INVALID_SPAN_CONTEXT:
            return

        sampled = (trace.TraceFlags.SAMPLED & span_context.trace_flags) != 0
        carrier[self.TRACE_ID_KEY] = format_trace_id(span_context.trace_id)
        carrier[self.SPAN_ID_KEY] = format_span_id(span_context.span_id)
        span_parent = getattr(span, "parent", None)
        if span_parent is not None:
            carrier[self.PARENT_SPAN_ID_KEY] = format_span_id(
                span_parent.span_id
            )
            carrier[self.SAMPLED_KEY] = "1" if sampled else "0"

    @property
    def fields(self) -> Set[str]:
        return {
            self.TRACE_ID_KEY,
            self.SPAN_ID_KEY,
            self.PARENT_SPAN_ID_KEY,
            self.SAMPLED_KEY,
        }
