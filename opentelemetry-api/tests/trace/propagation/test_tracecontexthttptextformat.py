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

# type: ignore

import typing
import unittest
from unittest.mock import Mock, patch

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace.propagation import tracecontext
from opentelemetry.trace.span import TraceState

FORMAT = tracecontext.TraceContextTextMapPropagator()


class TestTraceContextFormat(unittest.TestCase):
    TRACE_ID = int("12345678901234567890123456789012", 16)  # type:int
    SPAN_ID = int("1234567890123456", 16)  # type:int

    def test_no_traceparent_header(self):
        """When tracecontext headers are not present, a new SpanContext
        should be created.

        RFC 4.2.2:

        If no traceparent header is received, the vendor creates a new
        trace-id and parent-id that represents the current request.
        """
        output: typing.Dict[str, typing.List[str]] = {}
        span = trace.get_current_span(FORMAT.extract(output))
        self.assertIsInstance(span.get_span_context(), trace.SpanContext)

    def test_headers_with_tracestate(self):
        """When there is a traceparent and tracestate header, data from
        both should be added to the SpanContext.
        """
        traceparent_value = (
            f"00-{format(self.TRACE_ID, '032x')}-"
            f"{format(self.SPAN_ID, '016x')}-00"
        )
        tracestate_value = "foo=1,bar=2,baz=3"
        span_context = trace.get_current_span(
            FORMAT.extract(
                {
                    "traceparent": [traceparent_value],
                    "tracestate": [tracestate_value],
                },
            )
        ).get_span_context()
        self.assertEqual(span_context.trace_id, self.TRACE_ID)
        self.assertEqual(span_context.span_id, self.SPAN_ID)
        self.assertEqual(
            span_context.trace_state, {"foo": "1", "bar": "2", "baz": "3"}
        )
        self.assertTrue(span_context.is_remote)
        output: typing.Dict[str, str] = {}
        span = trace.NonRecordingSpan(span_context)

        ctx = trace.set_span_in_context(span)
        FORMAT.inject(output, context=ctx)
        self.assertEqual(output["traceparent"], traceparent_value)
        for pair in ["foo=1", "bar=2", "baz=3"]:
            self.assertIn(pair, output["tracestate"])
        self.assertEqual(output["tracestate"].count(","), 2)

    def test_invalid_trace_id(self):
        """If the trace id is invalid, we must ignore the full traceparent header,
        and return a random, valid trace.

        Also ignore any tracestate.

        RFC 3.2.2.3

        If the trace-id value is invalid (for example if it contains
        non-allowed characters or all zeros), vendors MUST ignore the
        traceparent.

        RFC 3.3

        If the vendor failed to parse traceparent, it MUST NOT attempt to
        parse tracestate.
        Note that the opposite is not true: failure to parse tracestate MUST
        NOT affect the parsing of traceparent.
        """
        span = trace.get_current_span(
            FORMAT.extract(
                {
                    "traceparent": [
                        "00-00000000000000000000000000000000-1234567890123456-00"
                    ],
                    "tracestate": ["foo=1,bar=2,foo=3"],
                },
            )
        )
        self.assertEqual(span.get_span_context(), trace.INVALID_SPAN_CONTEXT)

    def test_invalid_parent_id(self):
        """If the parent id is invalid, we must ignore the full traceparent
        header.

        Also ignore any tracestate.

        RFC 3.2.2.3

        Vendors MUST ignore the traceparent when the parent-id is invalid (for
        example, if it contains non-lowercase hex characters).

        RFC 3.3

        If the vendor failed to parse traceparent, it MUST NOT attempt to parse
        tracestate.
        Note that the opposite is not true: failure to parse tracestate MUST
        NOT affect the parsing of traceparent.
        """
        span = trace.get_current_span(
            FORMAT.extract(
                {
                    "traceparent": [
                        "00-00000000000000000000000000000000-0000000000000000-00"
                    ],
                    "tracestate": ["foo=1,bar=2,foo=3"],
                },
            )
        )
        self.assertEqual(span.get_span_context(), trace.INVALID_SPAN_CONTEXT)

    def test_no_send_empty_tracestate(self):
        """If the tracestate is empty, do not set the header.

        RFC 3.3.1.1

        Empty and whitespace-only list members are allowed. Vendors MUST accept
        empty tracestate headers but SHOULD avoid sending them.
        """
        output: typing.Dict[str, str] = {}
        span = trace.NonRecordingSpan(
            trace.SpanContext(self.TRACE_ID, self.SPAN_ID, is_remote=False)
        )
        ctx = trace.set_span_in_context(span)
        FORMAT.inject(output, context=ctx)
        self.assertTrue("traceparent" in output)
        self.assertFalse("tracestate" in output)

    def test_format_not_supported(self):
        """If the traceparent does not adhere to the supported format, discard it and
        create a new tracecontext.

        RFC 4.3

        If the version cannot be parsed, return an invalid trace header.
        """
        span = trace.get_current_span(
            FORMAT.extract(
                {
                    "traceparent": [
                        "00-12345678901234567890123456789012-"
                        "1234567890123456-00-residue"
                    ],
                    "tracestate": ["foo=1,bar=2,foo=3"],
                },
            )
        )
        self.assertEqual(span.get_span_context(), trace.INVALID_SPAN_CONTEXT)

    def test_propagate_invalid_context(self):
        """Do not propagate invalid trace context."""
        output: typing.Dict[str, str] = {}
        ctx = trace.set_span_in_context(trace.INVALID_SPAN)
        FORMAT.inject(output, context=ctx)
        self.assertFalse("traceparent" in output)

    def test_tracestate_empty_header(self):
        """Test tracestate with an additional empty header (should be ignored)"""
        span = trace.get_current_span(
            FORMAT.extract(
                {
                    "traceparent": [
                        "00-12345678901234567890123456789012-1234567890123456-00"
                    ],
                    "tracestate": ["foo=1", ""],
                },
            )
        )
        self.assertEqual(span.get_span_context().trace_state["foo"], "1")

    def test_tracestate_header_with_trailing_comma(self):
        """Do not propagate invalid trace context."""
        span = trace.get_current_span(
            FORMAT.extract(
                {
                    "traceparent": [
                        "00-12345678901234567890123456789012-1234567890123456-00"
                    ],
                    "tracestate": ["foo=1,"],
                },
            )
        )
        self.assertEqual(span.get_span_context().trace_state["foo"], "1")

    def test_tracestate_keys(self):
        """Test for valid key patterns in the tracestate"""
        tracestate_value = ",".join(
            [
                "1a-2f@foo=bar1",
                "1a-_*/2b@foo=bar2",
                "foo=bar3",
                "foo-_*/bar=bar4",
            ]
        )
        span = trace.get_current_span(
            FORMAT.extract(
                {
                    "traceparent": [
                        "00-12345678901234567890123456789012-"
                        "1234567890123456-00"
                    ],
                    "tracestate": [tracestate_value],
                },
            )
        )
        self.assertEqual(
            span.get_span_context().trace_state["1a-2f@foo"], "bar1"
        )
        self.assertEqual(
            span.get_span_context().trace_state["1a-_*/2b@foo"], "bar2"
        )
        self.assertEqual(span.get_span_context().trace_state["foo"], "bar3")
        self.assertEqual(
            span.get_span_context().trace_state["foo-_*/bar"], "bar4"
        )

    @patch("opentelemetry.trace.INVALID_SPAN_CONTEXT")
    @patch("opentelemetry.trace.get_current_span")
    def test_fields(self, mock_get_current_span, mock_invalid_span_context):

        mock_get_current_span.configure_mock(
            return_value=Mock(
                **{
                    "get_span_context.return_value": Mock(
                        **{
                            "trace_id": 1,
                            "span_id": 2,
                            "trace_flags": 3,
                            "trace_state": TraceState([("a", "b")]),
                        }
                    )
                }
            )
        )

        mock_setter = Mock()

        FORMAT.inject({}, setter=mock_setter)

        inject_fields = set()

        for mock_call in mock_setter.mock_calls:
            inject_fields.add(mock_call[1][1])

        self.assertEqual(inject_fields, FORMAT.fields)

    def test_extract_no_trace_parent_to_explicit_ctx(self):
        carrier = {"tracestate": ["foo=1"]}
        orig_ctx = Context({"k1": "v1"})

        ctx = FORMAT.extract(carrier, orig_ctx)
        self.assertDictEqual(orig_ctx, ctx)

    def test_extract_no_trace_parent_to_implicit_ctx(self):
        carrier = {"tracestate": ["foo=1"]}

        ctx = FORMAT.extract(carrier)
        self.assertDictEqual(Context(), ctx)

    def test_extract_invalid_trace_parent_to_explicit_ctx(self):
        trace_parent_headers = [
            "invalid",
            "00-00000000000000000000000000000000-1234567890123456-00",
            "00-12345678901234567890123456789012-0000000000000000-00",
            "00-12345678901234567890123456789012-1234567890123456-00-residue",
        ]
        for trace_parent in trace_parent_headers:
            with self.subTest(trace_parent=trace_parent):
                carrier = {
                    "traceparent": [trace_parent],
                    "tracestate": ["foo=1"],
                }
                orig_ctx = Context({"k1": "v1"})

                ctx = FORMAT.extract(carrier, orig_ctx)
                self.assertDictEqual(orig_ctx, ctx)

    def test_extract_invalid_trace_parent_to_implicit_ctx(self):
        trace_parent_headers = [
            "invalid",
            "00-00000000000000000000000000000000-1234567890123456-00",
            "00-12345678901234567890123456789012-0000000000000000-00",
            "00-12345678901234567890123456789012-1234567890123456-00-residue",
        ]
        for trace_parent in trace_parent_headers:
            with self.subTest(trace_parent=trace_parent):
                carrier = {
                    "traceparent": [trace_parent],
                    "tracestate": ["foo=1"],
                }

                ctx = FORMAT.extract(carrier)
                self.assertDictEqual(Context(), ctx)
