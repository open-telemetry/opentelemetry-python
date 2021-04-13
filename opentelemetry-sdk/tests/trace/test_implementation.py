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

from opentelemetry.sdk import trace
from opentelemetry.trace import invalid_span, invalid_span_context


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
            self.assertNotEqual(span.get_span_context(), invalid_span_context)
            self.assertNotEqual(span, invalid_span)
            self.assertIs(span.is_recording(), True)
            with tracer.start_span("test2") as span2:
                self.assertNotEqual(
                    span2.get_span_context(), invalid_span_context
                )
                self.assertNotEqual(span2, invalid_span)
                self.assertIs(span2.is_recording(), True)

    def test_span(self):
        with self.assertRaises(Exception):
            # pylint: disable=no-value-for-parameter
            span = trace._Span()

        span = trace._Span("name", invalid_span_context)
        self.assertEqual(span.get_span_context(), invalid_span_context)
        self.assertIs(span.is_recording(), True)
