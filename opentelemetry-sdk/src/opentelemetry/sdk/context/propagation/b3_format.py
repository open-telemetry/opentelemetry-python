# Copyright 2019, OpenTelemetry Authors
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
from opentelemetry.propagation import (
    Extractor,
    Getter,
    Injector,
    Setter,
    get_as_list,
    set_in_dict,
)
from opentelemetry.trace.propagation.context import (
    Context,
    span_context_from_context,
    with_span_context,
)

_T = typing.TypeVar("_T")

TRACE_ID_KEY = "x-b3-traceid"
SPAN_ID_KEY = "x-b3-spanid"
SAMPLED_KEY = "x-b3-sampled"


def http_propagator() -> typing.Tuple[Extractor, Injector]:
    """ TODO """
    return B3Extractor, B3Injector


class B3Extractor(Extractor):
    """Propagator for the B3 HTTP header format.

    See: https://github.com/openzipkin/b3-propagation
    """

    SINGLE_HEADER_KEY = "b3"
    FLAGS_KEY = "x-b3-flags"
    _SAMPLE_PROPAGATE_VALUES = set(["1", "True", "true", "d"])

    @classmethod
    def extract(
        cls,
        carrier,
        context: typing.Optional[Context] = None,
        get_from_carrier: typing.Optional[Getter[_T]] = get_as_list,
    ):

        trace_id = format_trace_id(trace.INVALID_TRACE_ID)
        span_id = format_span_id(trace.INVALID_SPAN_ID)
        sampled = "0"
        flags = None

        single_header = _extract_first_element(
            get_from_carrier(carrier, cls.SINGLE_HEADER_KEY)
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
                trace_id, span_id, sampled, _parent_span_id = fields
            else:
                return with_span_context(trace.INVALID_SPAN_CONTEXT)
        else:
            trace_id = (
                _extract_first_element(get_from_carrier(carrier, TRACE_ID_KEY))
                or trace_id
            )
            span_id = (
                _extract_first_element(get_from_carrier(carrier, SPAN_ID_KEY))
                or span_id
            )
            sampled = (
                _extract_first_element(get_from_carrier(carrier, SAMPLED_KEY))
                or sampled
            )
            flags = (
                _extract_first_element(
                    get_from_carrier(carrier, cls.FLAGS_KEY)
                )
                or flags
            )

        options = 0
        # The b3 spec provides no defined behavior for both sample and
        # flag values set. Since the setting of at least one implies
        # the desire for some form of sampling, propagate if either
        # header is set to allow.
        if sampled in cls._SAMPLE_PROPAGATE_VALUES or flags == "1":
            options |= trace.TraceOptions.SAMPLED

        return with_span_context(
            trace.SpanContext(
                # trace an span ids are encoded in hex, so must be converted
                trace_id=int(trace_id, 16),
                span_id=int(span_id, 16),
                trace_options=trace.TraceOptions(options),
                trace_state=trace.TraceState(),
            ),
        )


class B3Injector(Injector):
    @classmethod
    def inject(
        cls,
        carrier,
        context: typing.Optional[Context] = None,
        set_in_carrier: typing.Optional[Setter[_T]] = set_in_dict,
    ):
        sc = span_context_from_context(context)
        sampled = (trace.TraceOptions.SAMPLED & sc.trace_options) != 0
        set_in_carrier(carrier, TRACE_ID_KEY, format_trace_id(sc.trace_id))
        set_in_carrier(carrier, SPAN_ID_KEY, format_span_id(sc.span_id))
        set_in_carrier(carrier, SAMPLED_KEY, "1" if sampled else "0")


def format_trace_id(trace_id: int) -> str:
    """Format the trace id according to b3 specification."""
    return format(trace_id, "032x")


def format_span_id(span_id: int) -> str:
    """Format the span id according to b3 specification."""
    return format(span_id, "016x")


_T = typing.TypeVar("_T")


def _extract_first_element(items: typing.Iterable[_T]) -> typing.Optional[_T]:
    if items is None:
        return None
    return next(iter(items), None)
