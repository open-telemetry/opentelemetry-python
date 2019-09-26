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

import unittest

from opentelemetry import trace
from opentelemetry.context.propagation import tracecontexthttptextformat

FORMAT = tracecontexthttptextformat.TraceContextHTTPTextFormat()


def get_as_list(dict_object, key):
    value = dict_object.get(key)
    return [value] if value is not None else []


class TestTraceContextFormat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trace_id = int("12345678901234567890123456789012", 16)
        cls.span_id = int("1234567890123456", 16)

    def test_no_traceparent_header(self):
        """When tracecontext headers are not present, a new SpanContext
        should be created.

        RFC 4.2.2:

        If no traceparent header is received, the vendor creates a new trace-id and parent-id that represents the current request.
        """
        span_context = FORMAT.extract(get_as_list, {})
        self.assertTrue(isinstance(span_context, trace.SpanContext))

    def test_from_headers_tracestate_entry_limit(self):
        """If more than 32 entries are passed, do not propagate tracestate.

        RFC 3.3.1.1

        There can be a maximum of 32 list-members in a list.
        """

        span_context = FORMAT.extract(
            get_as_list,
            {
                "traceparent": "00-12345678901234567890123456789012-1234567890123456-00",
                "tracestate": ",".join(
                    [
                        "a00=0,a01=1,a02=2,a03=3,a04=4,a05=5,a06=6,a07=7,a08=8,a09=9",
                        "b00=0,b01=1,b02=2,b03=3,b04=4,b05=5,b06=6,b07=7,b08=8,b09=9",
                        "c00=0,c01=1,c02=2,c03=3,c04=4,c05=5,c06=6,c07=7,c08=8,c09=9",
                        "d00=0,d01=1,d02=2",
                    ]
                ),
            },
        )
        self.assertEqual(len(span_context.trace_state), 32)

    def test_from_headers_tracestate_duplicated_keys(self):
        """If a duplicate tracestate header is present, the most recent entry
        is used.

        RFC 3.3.1.4

        Only one entry per key is allowed because the entry represents that last position in the trace.
        Hence vendors must overwrite their entry upon reentry to their tracing system.

        For example, if a vendor name is Congo and a trace started in their system and then went through
        a system named Rojo and later returned to Congo, the tracestate value would not be:

        congo=congosFirstPosition,rojo=rojosFirstPosition,congo=congosSecondPosition

        Instead, the entry would be rewritten to only include the most recent position:

        congo=congosSecondPosition,rojo=rojosFirstPosition
        """
        span_context = FORMAT.extract(
            get_as_list,
            {
                "traceparent": "00-12345678901234567890123456789012-1234567890123456-00",
                "tracestate": "foo=1,bar=2,foo=3",
            },
        )
        self.assertEqual(span_context.trace_state, {"foo": "3", "bar": "2"})

    def test_headers_with_tracestate(self):
        """When there is a traceparent and tracestate header, data from
        both should be addded to the SpanContext.
        """
        traceparent_value = "00-{trace_id}-{span_id}-00".format(
            trace_id=format(self.trace_id, "032x"),
            span_id=format(self.span_id, "016x"),
        )
        tracestate_value = "foo=1,bar=2,baz=3"
        span_context = FORMAT.extract(
            get_as_list,
            {"traceparent": traceparent_value, "tracestate": tracestate_value},
        )
        self.assertEqual(span_context.trace_id, self.trace_id)
        self.assertEqual(span_context.span_id, self.span_id)
        self.assertEqual(
            span_context.trace_state, {"foo": "1", "bar": "2", "baz": "3"}
        )

        output = {}
        FORMAT.inject(span_context, dict.__setitem__, output)
        self.assertEqual(output["traceparent"], traceparent_value)
        self.assertEqual(output["tracestate"], tracestate_value)

    def test_invalid_trace_id(self):
        """If the trace id is invalid, we must ignore the full traceparent header.

        Also ignore any tracestate.

        RFC 3.2.2.3

        If the trace-id value is invalid (for example if it contains non-allowed characters or all
        zeros), vendors MUST ignore the traceparent.

        RFC 3.3

        If the vendor failed to parse traceparent, it MUST NOT attempt to parse tracestate.
        Note that the opposite is not true: failure to parse tracestate MUST NOT affect the parsing of traceparent.
        """
        span_context = FORMAT.extract(
            get_as_list,
            {
                "traceparent": "00-00000000000000000000000000000000-1234567890123456-00",
                "tracestate": "foo=1,bar=2,foo=3",
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
        span_context = FORMAT.extract(
            get_as_list,
            {
                "traceparent": "00-00000000000000000000000000000000-0000000000000000-00",
                "tracestate": "foo=1,bar=2,foo=3",
            },
        )
        self.assertEqual(span_context, trace.INVALID_SPAN_CONTEXT)

    def test_no_send_empty_tracestate(self):
        """If the tracestate is empty, do not set the header.

        RFC 3.3.1.1

        Empty and whitespace-only list members are allowed. Vendors MUST accept empty
        tracestate headers but SHOULD avoid sending them.
        """
        output = {}
        FORMAT.inject(
            trace.SpanContext(self.trace_id, self.span_id),
            dict.__setitem__,
            output,
        )
        self.assertTrue("traceparent" in output)
        self.assertFalse("tracestate" in output)

    def test_format_not_supported(self):
        """If the traceparent does not adhere to the supported format, discard it and
        create a new tracecontext.

        RFC 4.3

        If the version cannot be parsed, the vendor creates a new traceparent header and
        deletes tracestate.
        """
        span_context = FORMAT.extract(
            get_as_list,
            {
                "traceparent": "00-12345678901234567890123456789012-1234567890123456-00-residue",
                "tracestate": "foo=1,bar=2,foo=3",
            },
        )
        self.assertEqual(span_context, trace.INVALID_SPAN_CONTEXT)

    def test_propagate_invalid_context(self):
        """Do not propagate invalid trace context.
        """
        output = {}
        FORMAT.inject(trace.INVALID_SPAN_CONTEXT, dict.__setitem__, output)
        self.assertFalse("traceparent" in output)
