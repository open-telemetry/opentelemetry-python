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
from opentelemetry.context.propagation import httptextformat

_T = typing.TypeVar("_T")

#    Keys and values are strings of up to 256 printable US-ASCII characters.
#    Implementations should conform to the the `W3C Trace Context - Tracestate`_
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
    r"[\x20-\x2b\x2d-\x3c\x3e-\x7e]{0,255}[\x21-\x2b\x2d-\x3c\x3e-\x7e]?"
)

_DELIMITER_FORMAT = "[ \t]*,[ \t]*"
_MEMBER_FORMAT = "({})(=)({})".format(_KEY_FORMAT, _VALUE_FORMAT)

_DELIMITER_FORMAT_RE = re.compile(_DELIMITER_FORMAT)
_MEMBER_FORMAT_RE = re.compile(_MEMBER_FORMAT)

_TRACECONTEXT_MAXIMUM_TRACESTATE_KEYS = 32


class TraceContextHTTPTextFormat(httptextformat.HTTPTextFormat):
    """Extracts and injects using w3c TraceContext's headers.
    """

    _TRACEPARENT_HEADER_NAME = "traceparent"
    _TRACESTATE_HEADER_NAME = "tracestate"
    _TRACEPARENT_HEADER_FORMAT = (
        "^[ \t]*([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})"
        + "(-.*)?[ \t]*$"
    )
    _TRACEPARENT_HEADER_FORMAT_RE = re.compile(_TRACEPARENT_HEADER_FORMAT)

    @classmethod
    def extract(
        cls, get_from_carrier: httptextformat.Getter[_T], carrier: _T
    ) -> trace.SpanContext:
        """Extracts a valid SpanContext from the carrier.
        """
        header = get_from_carrier(carrier, cls._TRACEPARENT_HEADER_NAME)

        if not header:
            return trace.generate_span_context()

        match = re.search(cls._TRACEPARENT_HEADER_FORMAT_RE, header[0])
        if not match:
            return trace.generate_span_context()

        version = match.group(1)
        trace_id = match.group(2)
        span_id = match.group(3)
        trace_options = match.group(4)

        if trace_id == "0" * 32 or span_id == "0" * 16:
            return trace.generate_span_context()

        if version == "00":
            if match.group(5):
                return trace.generate_span_context()
        if version == "ff":
            return trace.generate_span_context()

        tracestate = trace.TraceState()
        for tracestate_header in get_from_carrier(
            carrier, cls._TRACESTATE_HEADER_NAME
        ):
            # typing.Dict's update is not recognized by pylint:
            # https://github.com/PyCQA/pylint/issues/2420
            tracestate.update(  # pylint:disable=E1101
                _parse_tracestate(tracestate_header)
            )
        if len(tracestate) > _TRACECONTEXT_MAXIMUM_TRACESTATE_KEYS:
            tracestate = trace.TraceState()

        span_context = trace.SpanContext(
            trace_id=int(trace_id, 16),
            span_id=int(span_id, 16),
            trace_options=trace.TraceOptions(trace_options),
            trace_state=tracestate,
        )

        return span_context

    @classmethod
    def inject(
        cls,
        context: trace.SpanContext,
        set_in_carrier: httptextformat.Setter[_T],
        carrier: _T,
    ) -> None:
        if context == trace.INVALID_SPAN_CONTEXT:
            return
        traceparent_string = "00-{:032x}-{:016x}-{:02x}".format(
            context.trace_id, context.span_id, context.trace_options
        )
        set_in_carrier(
            carrier, cls._TRACEPARENT_HEADER_NAME, traceparent_string
        )
        if context.trace_state:
            tracestate_string = _format_tracestate(context.trace_state)
            set_in_carrier(
                carrier, cls._TRACESTATE_HEADER_NAME, tracestate_string
            )


def _parse_tracestate(string: str) -> trace.TraceState:
    """Parse a w3c tracestate header into a TraceState.

    Args:
        string: the value of the tracestate header.

    Returns:
        A valid TraceState that contains values extracted from
        the tracestate header.

        If the format of the TraceState is illegal, all values will
        be discarded and an empty tracestate will be returned.
    """
    tracestate = trace.TraceState()
    for member in re.split(_DELIMITER_FORMAT_RE, string):
        match = _MEMBER_FORMAT_RE.fullmatch(member)
        if not match:
            # TODO: log this?
            return trace.TraceState()
        key, _eq, value = match.groups()
        # typing.Dict's update is not recognized by pylint:
        # https://github.com/PyCQA/pylint/issues/2420
        tracestate[key] = value  # pylint:disable=E1137
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
