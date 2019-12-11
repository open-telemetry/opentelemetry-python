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
import unittest

from opentelemetry import trace
from opentelemetry.context import BaseRuntimeContext, Context
from opentelemetry.context.propagation import tracecontexthttptextformat
from opentelemetry.context.propagation.tracecontexthttptextformat import (
    TraceContextHTTPTextFormat,
)
from opentelemetry.trace.propagation import ContextKeys

INJECT = TraceContextHTTPTextFormat
EXTRACT = TraceContextHTTPTextFormat


def get_as_list(
    dict_object: typing.Dict[str, typing.List[str]], key: str
) -> typing.List[str]:
    value = dict_object.get(key)
    return value if value is not None else []


class TestTraceContextFormat(unittest.TestCase):
    TRACE_ID = int("12345678901234567890123456789012", 16)  # type:int
    SPAN_ID = int("1234567890123456", 16)  # type:int

    def setUp(self):
        self.ctx = BaseRuntimeContext.current()

    def test_no_traceparent_header(self):
        """When tracecontext headers are not present, a new SpanContext
        should be created.

        RFC 4.2.2:

        If no traceparent header is received, the vendor creates a new trace-id and parent-id that represents the current request.
        """
        output = {}  # type:typing.Dict[str, typing.List[str]]
        span_context = EXTRACT.extract(self.ctx, get_as_list, output)
        self.assertTrue(isinstance(span_context, trace.SpanContext))

    def test_headers_with_tracestate(self):
        """When there is a traceparent and tracestate header, data from
        both should be addded to the SpanContext.
        """
        traceparent_value = "00-{trace_id}-{span_id}-00".format(
            trace_id=format(self.TRACE_ID, "032x"),
            span_id=format(self.SPAN_ID, "016x"),
        )
        tracestate_value = "foo=1,bar=2,baz=3"
        ctx = EXTRACT.extract(
            self.ctx,
            get_as_list,
            {
                "traceparent": [traceparent_value],
                "tracestate": [tracestate_value],
            },
        )
        span_context = BaseRuntimeContext.value(
            ctx, ContextKeys.span_context_key()
        )
        self.assertEqual(span_context.trace_id, self.TRACE_ID)
        self.assertEqual(span_context.span_id, self.SPAN_ID)
        self.assertEqual(
            span_context.trace_state, {"foo": "1", "bar": "2", "baz": "3"}
        )

        output = {}  # type:typing.Dict[str, str]
        INJECT.inject(self.ctx, dict.__setitem__, output)
        self.assertEqual(output["traceparent"], traceparent_value)
        for pair in ["foo=1", "bar=2", "baz=3"]:
            self.assertIn(pair, output["tracestate"])
        self.assertEqual(output["tracestate"].count(","), 2)

    def test_invalid_trace_id(self):
        """If the trace id is invalid, we must ignore the full traceparent header,
        and return a random, valid trace.

        Also ignore any tracestate.

        RFC 3.2.2.3

        If the trace-id value is invalid (for example if it contains non-allowed characters or all
        zeros), vendors MUST ignore the traceparent.

        RFC 3.3

        If the vendor failed to parse traceparent, it MUST NOT attempt to parse tracestate.
        Note that the opposite is not true: failure to parse tracestate MUST NOT affect the parsing of traceparent.
        """
        span_context = EXTRACT.extract(
            self.ctx,
            get_as_list,
            {
                "traceparent": [
                    "00-00000000000000000000000000000000-1234567890123456-00"
                ],
                "tracestate": ["foo=1,bar=2,foo=3"],
            },
        )
        self.assertEqual(span_context, trace.INVALID_SPAN_CONTEXT)

    def test_invalid_parent_id(self):
        """If the parent id is invalid, we must ignore the full traceparent header.

        Also ignore any tracestate.

        RFC 3.2.2.3

        Vendors MUST ignore the traceparent when the parent-id is invalid (for example,
        if it contains non-lowercase hex characters).

        RFC 3.3

        If the vendor failed to parse traceparent, it MUST NOT attempt to parse tracestate.
        Note that the opposite is not true: failure to parse tracestate MUST NOT affect the parsing of traceparent.
        """
        span_context = EXTRACT.extract(
            self.ctx,
            get_as_list,
            {
                "traceparent": [
                    "00-00000000000000000000000000000000-0000000000000000-00"
                ],
                "tracestate": ["foo=1,bar=2,foo=3"],
            },
        )
        self.assertEqual(span_context, trace.INVALID_SPAN_CONTEXT)

    def test_no_send_empty_tracestate(self):
        """If the tracestate is empty, do not set the header.

        RFC 3.3.1.1

        Empty and whitespace-only list members are allowed. Vendors MUST accept empty
        tracestate headers but SHOULD avoid sending them.
        """
        ctx = BaseRuntimeContext.set_value(
            self.ctx,
            ContextKeys.span_context_key(),
            trace.SpanContext(self.TRACE_ID, self.SPAN_ID),
        )
        output = {}  # type:typing.Dict[str, str]
        INJECT.inject(
            ctx, dict.__setitem__, output,
        )
        self.assertTrue("traceparent" in output)
        self.assertFalse("tracestate" in output)

    def test_format_not_supported(self):
        """If the traceparent does not adhere to the supported format, discard it and
        create a new tracecontext.

        RFC 4.3

        If the version cannot be parsed, return an invalid trace header.
        """
        span_context = EXTRACT.extract(
            self.ctx,
            get_as_list,
            {
                "traceparent": [
                    "00-12345678901234567890123456789012-1234567890123456-00-residue"
                ],
                "tracestate": ["foo=1,bar=2,foo=3"],
            },
        )
        self.assertEqual(span_context, trace.INVALID_SPAN_CONTEXT)

    def test_propagate_invalid_context(self):
        """Do not propagate invalid trace context.
        """
        output = {}  # type:typing.Dict[str, str]
        ctx = BaseRuntimeContext.set_value(
            self.ctx,
            ContextKeys.span_context_key(),
            trace.INVALID_SPAN_CONTEXT,
        )
        INJECT.inject(ctx, dict.__setitem__, output)
        self.assertFalse("traceparent" in output)

    def test_tracestate_empty_header(self):
        """Test tracestate with an additional empty header (should be ignored)"""
        ctx = EXTRACT.extract(
            self.ctx,
            get_as_list,
            {
                "traceparent": [
                    "00-12345678901234567890123456789012-1234567890123456-00"
                ],
                "tracestate": ["foo=1", ""],
            },
        )
        span_context = BaseRuntimeContext.value(
            ctx, ContextKeys.span_context_key()
        )
        self.assertEqual(span_context.trace_state["foo"], "1")

    def test_tracestate_header_with_trailing_comma(self):
        """Do not propagate invalid trace context.
        """
        ctx = EXTRACT.extract(
            self.ctx,
            get_as_list,
            {
                "traceparent": [
                    "00-12345678901234567890123456789012-1234567890123456-00"
                ],
                "tracestate": ["foo=1,"],
            },
        )
        span_context = BaseRuntimeContext.value(
            ctx, ContextKeys.span_context_key()
        )
        self.assertEqual(span_context.trace_state["foo"], "1")
