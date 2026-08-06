# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest

from opentelemetry.sdk import trace
from opentelemetry.trace import INVALID_SPAN, INVALID_SPAN_CONTEXT


class TestTracerImplementation(unittest.TestCase):
    """
    This test is in place to ensure the SDK implementation of the API
    is returning values that are valid. The same tests have been added
    to the API with different expected results. See issue for more details:
    https://github.com/open-telemetry/opentelemetry-python/issues/142
    """

    def test_tracer(self):
        tracer = trace.TracerProvider().get_tracer(__name__)
        with tracer.start_span("test") as span:
            self.assertNotEqual(span.get_span_context(), INVALID_SPAN_CONTEXT)
            self.assertNotEqual(span, INVALID_SPAN)
            self.assertIs(span.is_recording(), True)
            with tracer.start_span("test2") as span2:
                self.assertNotEqual(
                    span2.get_span_context(), INVALID_SPAN_CONTEXT
                )
                self.assertNotEqual(span2, INVALID_SPAN)
                self.assertIs(span2.is_recording(), True)

    def test_span(self):
        with self.assertRaises(Exception):
            # pylint: disable=no-value-for-parameter
            span = trace._Span()

        span = trace._Span("name", INVALID_SPAN_CONTEXT)
        self.assertEqual(span.get_span_context(), INVALID_SPAN_CONTEXT)
        self.assertIs(span.is_recording(), True)
