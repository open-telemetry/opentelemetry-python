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

import unittest

from opentelemetry import trace


class TestAPIOnlyImplementation(unittest.TestCase):
    """
    This test is in place to ensure the API is returning values that
    are valid. The same tests have been added to the SDK with
    different expected results. See issue for more details:
    https://github.com/open-telemetry/opentelemetry-python/issues/142
    """

    # TRACER

    def test_tracer(self):
        with self.assertRaises(TypeError):
            # pylint: disable=abstract-class-instantiated
            trace.TracerProvider()  # type:ignore

    def test_default_tracer(self):
        tracer_provider = trace.NoOpTracerProvider()
        tracer = tracer_provider.get_tracer(__name__)
        with tracer.start_span("test") as span:
            self.assertEqual(
                span.get_span_context(), trace.INVALID_SPAN_CONTEXT
            )
            self.assertEqual(span, trace.INVALID_SPAN)
            self.assertIs(span.is_recording(), False)
            with tracer.start_span("test2") as span2:
                self.assertEqual(
                    span2.get_span_context(), trace.INVALID_SPAN_CONTEXT
                )
                self.assertEqual(span2, trace.INVALID_SPAN)
                self.assertIs(span2.is_recording(), False)

    def test_span(self):
        with self.assertRaises(TypeError):
            # pylint: disable=abstract-class-instantiated
            trace.Span()  # type:ignore

    def test_default_span(self):
        span = trace.NonRecordingSpan(trace.INVALID_SPAN_CONTEXT)
        self.assertEqual(span.get_span_context(), trace.INVALID_SPAN_CONTEXT)
        self.assertIs(span.is_recording(), False)
