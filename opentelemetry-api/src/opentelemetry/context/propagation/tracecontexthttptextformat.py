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
#
import re
import typing

import opentelemetry.trace as trace
from opentelemetry.context import Context
from opentelemetry.context.propagation import (
    Getter,
    HTTPExtractor,
    HTTPInjector,
    Setter,
    get_as_list,
    set_in_dict,
)
from opentelemetry.trace.propagation.context import (
    from_context,
    with_span_context,
)

_T = typing.TypeVar("_T")

#    Keys and values are strings of up to 256 printable US-ASCII characters.
#    Implementations should conform to the `W3C Trace Context - Tracestate`_
#    spec, which describes additional restrictions on valid field values.
#
#    .. _W3C Trace Context - Tracestate:
#        https://www.w3.org/TR/trace-context/#tracestate-field


_KEY_WITHOUT_VENDOR_FORMAT = r"[a-z][_0-9a-z\-\*\/]{0,255}"
_KEY_WITH_VENDOR_FORMAT = (
    r"[a-z][_0-9a-z\-\*\/]{0,240}@[a-z][_0-9a-z\-\*\/]{0,13}"
)

_KEY_FORMAT = _KEY_WITHOUT_VENDOR_FORMAT + "|" + _KEY_WITH_VENDOR_FORMAT
_VALUE_FORMAT = (
    r"[\x20-\x2b\x2d-\x3c\x3e-\x7e]{0,255}[\x21-\x2b\x2d-\x3c\x3e-\x7e]"
)

_DELIMITER_FORMAT = "[ \t]*,[ \t]*"
_MEMBER_FORMAT = "({})(=)({})[ \t]*".format(_KEY_FORMAT, _VALUE_FORMAT)

_DELIMITER_FORMAT_RE = re.compile(_DELIMITER_FORMAT)
_MEMBER_FORMAT_RE = re.compile(_MEMBER_FORMAT)

_TRACECONTEXT_MAXIMUM_TRACESTATE_KEYS = 32


TRACEPARENT_HEADER_NAME = "traceparent"
TRACESTATE_HEADER_NAME = "tracestate"


class TraceContextHTTPExtractor(HTTPExtractor):
    """Extracts using w3c TraceContext's headers.
    """

    _TRACEPARENT_HEADER_FORMAT = (
        "^[ \t]*([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})"
        + "(-.*)?[ \t]*$"
    )
    _TRACEPARENT_HEADER_FORMAT_RE = re.compile(_TRACEPARENT_HEADER_FORMAT)

    @classmethod
    def extract(
        cls,
        carrier: _T,
        context: typing.Optional[Context] = None,
        get_from_carrier: typing.Optional[Getter[_T]] = get_as_list,
    ) -> Context:
        """Extracts a valid SpanContext from the carrier.
        """
        header = get_from_carrier(carrier, TRACEPARENT_HEADER_NAME)

        if not header:
            return with_span_context(trace.INVALID_SPAN_CONTEXT)

        match = re.search(cls._TRACEPARENT_HEADER_FORMAT_RE, header[0])
        if not match:
            return with_span_context(trace.INVALID_SPAN_CONTEXT)

        version = match.group(1)
        trace_id = match.group(2)
        span_id = match.group(3)
        trace_options = match.group(4)

        if trace_id == "0" * 32 or span_id == "0" * 16:
            return with_span_context(trace.INVALID_SPAN_CONTEXT)

        if version == "00":
            if match.group(5):
                return with_span_context(trace.INVALID_SPAN_CONTEXT)
        if version == "ff":
            return with_span_context(trace.INVALID_SPAN_CONTEXT)

        tracestate_headers = get_from_carrier(carrier, TRACESTATE_HEADER_NAME)
        tracestate = _parse_tracestate(tracestate_headers)

        return with_span_context(
            trace.SpanContext(
                trace_id=int(trace_id, 16),
                span_id=int(span_id, 16),
                trace_options=trace.TraceOptions(trace_options),
                trace_state=tracestate,
            )
        )


class TraceContextHTTPInjector(HTTPInjector):
    """Injects using w3c TraceContext's headers.
    """

    @classmethod
    def inject(
        cls,
        carrier: _T,
        context: typing.Optional[Context] = None,
        set_in_carrier: typing.Optional[Setter[_T]] = set_in_dict,
    ) -> None:
        sc = from_context(context)
        if sc is None or sc == trace.INVALID_SPAN_CONTEXT:
            return

        if (
            sc.trace_id == trace.INVALID_TRACE_ID
            or sc.span_id == trace.INVALID_SPAN_ID
        ):
            return

        traceparent_string = "00-{:032x}-{:016x}-{:02x}".format(
            sc.trace_id, sc.span_id, sc.trace_options,
        )
        set_in_carrier(carrier, TRACEPARENT_HEADER_NAME, traceparent_string)
        if sc.trace_state:
            tracestate_string = _format_tracestate(sc.trace_state)
            set_in_carrier(carrier, TRACESTATE_HEADER_NAME, tracestate_string)


def _parse_tracestate(header_list: typing.List[str]) -> trace.TraceState:
    """Parse one or more w3c tracestate header into a TraceState.

    Args:
        string: the value of the tracestate header.

    Returns:
        A valid TraceState that contains values extracted from
        the tracestate header.

        If the format of one headers is illegal, all values will
        be discarded and an empty tracestate will be returned.

        If the number of keys is beyond the maximum, all values
        will be discarded and an empty tracestate will be returned.
    """
    tracestate = trace.TraceState()
    value_count = 0
    for header in header_list:
        for member in re.split(_DELIMITER_FORMAT_RE, header):
            # empty members are valid, but no need to process further.
            if not member:
                continue
            match = _MEMBER_FORMAT_RE.fullmatch(member)
            if not match:
                # TODO: log this?
                return trace.TraceState()
            key, _eq, value = match.groups()
            if key in tracestate:  # pylint:disable=E1135
                # duplicate keys are not legal in
                # the header, so we will remove
                return trace.TraceState()
            # typing.Dict's update is not recognized by pylint:
            # https://github.com/PyCQA/pylint/issues/2420
            tracestate[key] = value  # pylint:disable=E1137
            value_count += 1
            if value_count > _TRACECONTEXT_MAXIMUM_TRACESTATE_KEYS:
                return trace.TraceState()
    return tracestate


def _format_tracestate(tracestate: trace.TraceState) -> str:
    """Parse a w3c tracestate header into a TraceState.

    Args:
        tracestate: the tracestate header to write

    Returns:
        A string that adheres to the w3c tracestate
        header format.
    """
    return ",".join(key + "=" + value for key, value in tracestate.items())
