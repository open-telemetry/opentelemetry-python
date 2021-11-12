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
from re import compile as re_compile

from deprecated import deprecated

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
from opentelemetry.trace import format_span_id, format_trace_id


class B3MultiFormat(TextMapPropagator):
    """Propagator for the B3 HTTP multi-header format.

    See: https://github.com/openzipkin/b3-propagation
         https://github.com/openzipkin/b3-propagation#multiple-headers
    """

    SINGLE_HEADER_KEY = "b3"
    TRACE_ID_KEY = "x-b3-traceid"
    SPAN_ID_KEY = "x-b3-spanid"
    SAMPLED_KEY = "x-b3-sampled"
    FLAGS_KEY = "x-b3-flags"
    _SAMPLE_PROPAGATE_VALUES = {"1", "True", "true", "d"}
    _trace_id_regex = re_compile(r"[\da-fA-F]{16}|[\da-fA-F]{32}")
    _span_id_regex = re_compile(r"[\da-fA-F]{16}")

    def extract(
        self,
        carrier: CarrierT,
        context: typing.Optional[Context] = None,
        getter: Getter = default_getter,
    ) -> Context:
        if context is None:
            context = Context()
        trace_id = trace.INVALID_TRACE_ID
        span_id = trace.INVALID_SPAN_ID
        sampled = "0"
        flags = None

        single_header = _extract_first_element(
            getter.get(carrier, self.SINGLE_HEADER_KEY)
        )
        if single_header:
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
            trace_id = (
                _extract_first_element(getter.get(carrier, self.TRACE_ID_KEY))
                or trace_id
            )
            span_id = (
                _extract_first_element(getter.get(carrier, self.SPAN_ID_KEY))
                or span_id
            )
            sampled = (
                _extract_first_element(getter.get(carrier, self.SAMPLED_KEY))
                or sampled
            )
            flags = (
                _extract_first_element(getter.get(carrier, self.FLAGS_KEY))
                or flags
            )

        if (
            trace_id == trace.INVALID_TRACE_ID
            or span_id == trace.INVALID_SPAN_ID
            or self._trace_id_regex.fullmatch(trace_id) is None
            or self._span_id_regex.fullmatch(span_id) is None
        ):
            return context

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
            ),
            context,
        )

    def inject(
        self,
        carrier: CarrierT,
        context: typing.Optional[Context] = None,
        setter: Setter = default_setter,
    ) -> None:
        span = trace.get_current_span(context=context)

        span_context = span.get_span_context()
        if span_context == trace.INVALID_SPAN_CONTEXT:
            return

        sampled = (trace.TraceFlags.SAMPLED & span_context.trace_flags) != 0
        setter.set(
            carrier,
            self.TRACE_ID_KEY,
            format_trace_id(span_context.trace_id),
        )
        setter.set(
            carrier, self.SPAN_ID_KEY, format_span_id(span_context.span_id)
        )
        setter.set(carrier, self.SAMPLED_KEY, "1" if sampled else "0")

    @property
    def fields(self) -> typing.Set[str]:
        return {
            self.TRACE_ID_KEY,
            self.SPAN_ID_KEY,
            self.SAMPLED_KEY,
        }


class B3SingleFormat(B3MultiFormat):
    """Propagator for the B3 HTTP single-header format.

    See: https://github.com/openzipkin/b3-propagation
         https://github.com/openzipkin/b3-propagation#single-header
    """

    def inject(
        self,
        carrier: CarrierT,
        context: typing.Optional[Context] = None,
        setter: Setter = default_setter,
    ) -> None:
        span = trace.get_current_span(context=context)

        span_context = span.get_span_context()
        if span_context == trace.INVALID_SPAN_CONTEXT:
            return

        sampled = (trace.TraceFlags.SAMPLED & span_context.trace_flags) != 0

        fields = [
            format_trace_id(span_context.trace_id),
            format_span_id(span_context.span_id),
            "1" if sampled else "0",
        ]

        setter.set(carrier, self.SINGLE_HEADER_KEY, "-".join(fields))

    @property
    def fields(self) -> typing.Set[str]:
        return {self.SINGLE_HEADER_KEY}


class B3Format(B3MultiFormat):
    @deprecated(
        version="1.2.0",
        reason="B3Format is deprecated in favor of B3MultiFormat",
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def _extract_first_element(
    items: typing.Iterable[CarrierT],
) -> typing.Optional[CarrierT]:
    if items is None:
        return None
    return next(iter(items), None)
