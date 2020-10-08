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

import opentelemetry.trace as trace
from opentelemetry.context import Context
from opentelemetry.trace.propagation.textmap import (
    Getter,
    Setter,
    TextMapPropagator,
    TextMapPropagatorT,
)
from opentelemetry import baggage

class JaegerFormat(TextMapPropagator):
    """Propagator for the Jaeger format.

    See: https://www.jaegertracing.io/docs/1.19/client-libraries/#propagation-format
    """

    TRACE_ID_KEY = 'uber-trace-id'
    def inject(
        self,
        set_in_carrier: Setter[TextMapPropagatorT],
        carrier: TextMapPropagatorT,
        context: typing.Optional[Context] = None,
    ) -> None:
        span = trace.get_current_span(context=context)
        span_context = span.get_context()
        if span_context == trace.INVALID_SPAN_CONTEXT:
            return

        # set span identity
        span_parent_id = getattr(span, "parent", 0)
        set_in_carrier(
            carrier, self.TRACE_ID_KEY, _format_trace_id(span_context.trace_id, span_context.span_id, span_parent_id, span_context.trace_flags)
        )

        # set span baggage, if any
        baggage_entries = baggage.get_all(context=context)
        if not baggage_entries:
            return

        for key, value in baggage_entries.items():
            baggage_key = 'uberctx-{}'.format(key)
            set_in_carrier(
              carrier, baggage_key, value
            )


def _format_trace_id(trace_id, span_id, parent_span_id, flags):
    return '{:032x}:{:016x}:{:016x}:{:02x}'.format(trace_id, span_id, parent_span_id, flags)




