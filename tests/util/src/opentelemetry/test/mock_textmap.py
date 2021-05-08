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
from opentelemetry.propagators.textmap import (
    CarrierT,
    Getter,
    Setter,
    TextMapPropagator,
    default_getter,
    default_setter,
)


class NOOPTextMapPropagator(TextMapPropagator):
    """A propagator that does not extract nor inject.

    This class is useful for catching edge cases assuming
    a SpanContext will always be present.
    """

    def extract(
        self,
        carrier: CarrierT,
        context: typing.Optional[Context] = None,
        getter: Getter = default_getter,
    ) -> Context:
        return Context()

    def inject(
        self,
        carrier: CarrierT,
        context: typing.Optional[Context] = None,
        setter: Setter = default_setter,
    ) -> None:
        return None

    @property
    def fields(self):
        return set()


class MockTextMapPropagator(TextMapPropagator):
    """Mock propagator for testing purposes."""

    TRACE_ID_KEY = "mock-traceid"
    SPAN_ID_KEY = "mock-spanid"

    def extract(
        self,
        carrier: CarrierT,
        context: typing.Optional[Context] = None,
        getter: Getter = default_getter,
    ) -> Context:
        if context is None:
            context = Context()
        trace_id_list = getter.get(carrier, self.TRACE_ID_KEY)
        span_id_list = getter.get(carrier, self.SPAN_ID_KEY)

        if not trace_id_list or not span_id_list:
            return context

        return trace.set_span_in_context(
            trace.NonRecordingSpan(
                trace.SpanContext(
                    trace_id=int(trace_id_list[0]),
                    span_id=int(span_id_list[0]),
                    is_remote=True,
                )
            ),
            context,
        )

    def inject(
        self,
        carrier: CarrierT,
        context: typing.Optional[Context] = None,
        setter: Setter = default_setter,
    ) -> None:
        span = trace.get_current_span(context)
        setter.set(
            carrier, self.TRACE_ID_KEY, str(span.get_span_context().trace_id)
        )
        setter.set(
            carrier, self.SPAN_ID_KEY, str(span.get_span_context().span_id)
        )

    @property
    def fields(self):
        return {self.TRACE_ID_KEY, self.SPAN_ID_KEY}
