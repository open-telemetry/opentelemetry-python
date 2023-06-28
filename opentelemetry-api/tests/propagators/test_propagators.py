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

from importlib import reload
from os import environ
from unittest import TestCase
from unittest.mock import Mock, patch

from opentelemetry import trace
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.context.context import Context
from opentelemetry.environment_variables import OTEL_PROPAGATORS
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)


class TestPropagators(TestCase):
    @patch("opentelemetry.propagators.composite.CompositePropagator")
    def test_default_composite_propagators(self, mock_compositehttppropagator):
        def test_propagators(propagators):

            propagators = {propagator.__class__ for propagator in propagators}

            self.assertEqual(len(propagators), 2)
            self.assertEqual(
                propagators,
                {TraceContextTextMapPropagator, W3CBaggagePropagator},
            )

        mock_compositehttppropagator.configure_mock(
            **{"side_effect": test_propagators}
        )

        # pylint: disable=import-outside-toplevel
        import opentelemetry.propagate

        reload(opentelemetry.propagate)

    @patch.dict(environ, {OTEL_PROPAGATORS: "a,  b,   c  "})
    @patch("opentelemetry.propagators.composite.CompositePropagator")
    @patch("opentelemetry.util._importlib_metadata.entry_points")
    def test_non_default_propagators(
        self, mock_entry_points, mock_compositehttppropagator
    ):

        mock_entry_points.configure_mock(
            **{
                "side_effect": [
                    [
                        Mock(
                            **{
                                "load.return_value": Mock(
                                    **{"return_value": "a"}
                                )
                            }
                        ),
                    ],
                    [
                        Mock(
                            **{
                                "load.return_value": Mock(
                                    **{"return_value": "b"}
                                )
                            }
                        )
                    ],
                    [
                        Mock(
                            **{
                                "load.return_value": Mock(
                                    **{"return_value": "c"}
                                )
                            }
                        )
                    ],
                ]
            }
        )

        def test_propagators(propagators):
            self.assertEqual(propagators, ["a", "b", "c"])

        mock_compositehttppropagator.configure_mock(
            **{"side_effect": test_propagators}
        )

        # pylint: disable=import-outside-toplevel
        import opentelemetry.propagate

        reload(opentelemetry.propagate)

    @patch.dict(
        environ, {OTEL_PROPAGATORS: "tracecontext , unknown , baggage"}
    )
    def test_composite_propagators_error(self):

        with self.assertRaises(ValueError) as cm:
            # pylint: disable=import-outside-toplevel
            import opentelemetry.propagate

            reload(opentelemetry.propagate)

        self.assertEqual(
            str(cm.exception),
            "Propagator unknown not found. It is either misspelled or not installed.",
        )


class TestTraceContextTextMapPropagator(TestCase):
    def setUp(self):
        self.propagator = TraceContextTextMapPropagator()

    def traceparent_helper(
        self,
        carrier,
    ):
        # We purposefully start with an empty context so we can test later if anything is added to it.
        initial_context = Context()

        context = self.propagator.extract(carrier, context=initial_context)
        self.assertIsNotNone(context)
        self.assertIsInstance(context, Context)

        return context

    def traceparent_helper_generator(
        self,
        version=0x00,
        trace_id=0x00000000000000000000000000000001,
        span_id=0x0000000000000001,
        trace_flags=0x00,
        suffix="",
    ):
        traceparent = f"{version:02x}-{trace_id:032x}-{span_id:016x}-{trace_flags:02x}{suffix}"
        carrier = {"traceparent": traceparent}
        return self.traceparent_helper(carrier)

    def valid_traceparent_helper(
        self,
        version=0x00,
        trace_id=0x00000000000000000000000000000001,
        span_id=0x0000000000000001,
        trace_flags=0x00,
        suffix="",
        assert_context_msg="A valid traceparent was provided, so the context should be non-empty.",
    ):
        context = self.traceparent_helper_generator(
            version=version,
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=trace_flags,
            suffix=suffix,
        )

        self.assertNotEqual(
            context,
            Context(),
            assert_context_msg,
        )

        span = trace.get_current_span(context)
        self.assertIsNotNone(span)
        self.assertIsInstance(span, trace.span.Span)

        span_context = span.get_span_context()
        self.assertIsNotNone(span_context)
        self.assertIsInstance(span_context, trace.span.SpanContext)

        # Note: No version in SpanContext, it is only used locally in TraceContextTextMapPropagator
        self.assertEqual(span_context.trace_id, trace_id)
        self.assertEqual(span_context.span_id, span_id)
        self.assertEqual(span_context.trace_flags, trace_flags)

        self.assertIsInstance(span_context.trace_state, trace.TraceState)
        self.assertCountEqual(span_context.trace_state, [])
        self.assertEqual(span_context.is_remote, True)

        return context, span, span_context

    def invalid_traceparent_helper(
        self,
        version=0x00,
        trace_id=0x00000000000000000000000000000001,
        span_id=0x0000000000000001,
        trace_flags=0x00,
        suffix="",
        assert_context_msg="An invalid traceparent was provided, so the context should still be empty.",
    ):
        context = self.traceparent_helper_generator(
            version=version,
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=trace_flags,
            suffix=suffix,
        )

        self.assertEqual(
            context,
            Context(),
            assert_context_msg,
        )

        return context

    def test_extract_nothing(self):
        context = self.traceparent_helper(carrier={})
        self.assertEqual(
            context,
            {},
            "We didn't provide a valid traceparent, so we should still have an empty Context.",
        )

    def test_extract_simple_traceparent(self):
        self.valid_traceparent_helper()

    # https://www.w3.org/TR/trace-context/#version
    def test_extract_version_forbidden_ff(self):
        self.invalid_traceparent_helper(
            version=0xFF,
            assert_context_msg="We provided ann invalid traceparent with a forbidden version=0xff, so the context should still be empty.",
        )

    # https://www.w3.org/TR/trace-context/#version-format
    def test_extract_version_00_with_unsupported_suffix(self):
        self.invalid_traceparent_helper(
            suffix="-f00",
            assert_context_msg="We provided an invalid traceparent with version=0x00 and suffix information which is not supported in this version, so the context should still be empty.",
        )

    # https://www.w3.org/TR/trace-context/#versioning-of-traceparent
    # See the parsing of the sampled bit of flags.
    def test_extract_future_version_with_future_suffix_data(self):
        self.valid_traceparent_helper(
            version=0x99,
            suffix="-f00",
            assert_context_msg="We provided a traceparent that is possibly valid in the future with version=0x99 and suffix information, so the context be non-empty.",
        )

    # https://www.w3.org/TR/trace-context/#trace-id
    def test_extract_trace_id_invalid_all_zeros(self):
        self.invalid_traceparent_helper(trace_id=0)

    # https://www.w3.org/TR/trace-context/#parent-id
    def test_extract_span_id_invalid_all_zeros(self):
        self.invalid_traceparent_helper(span_id=0)

    def test_extract_non_decimal_trace_flags(self):
        self.valid_traceparent_helper(trace_flags=0xA0)
