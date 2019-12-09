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

from opentelemetry.metrics import DefaultMetric
from opentelemetry.sdk import metrics, trace
from opentelemetry.trace import INVALID_SPAN, INVALID_SPAN_CONTEXT


class TestSDKImplementation(unittest.TestCase):
    """
    This test is in place to ensure the SDK implementation of the API
    is returning values that are valid. The same tests have been added
    to the API with different expected results. See issue for more details:
    https://github.com/open-telemetry/opentelemetry-python/issues/142
    """

    def test_tracer(self):
        tracer = trace.TracerSource().get_tracer("opentelemetery-sdk")
        with tracer.start_span("test") as span:
            self.assertNotEqual(span.get_context(), INVALID_SPAN_CONTEXT)
            self.assertNotEqual(span, INVALID_SPAN)
            self.assertIs(span.is_recording_events(), True)
            with tracer.start_span("test2") as span2:
                self.assertNotEqual(span2.get_context(), INVALID_SPAN_CONTEXT)
                self.assertNotEqual(span2, INVALID_SPAN)
                self.assertIs(span2.is_recording_events(), True)

    def test_span(self):
        with self.assertRaises(Exception):
            # pylint: disable=no-value-for-parameter
            span = trace.Span()

        span = trace.Span("name", INVALID_SPAN_CONTEXT)
        self.assertEqual(span.get_context(), INVALID_SPAN_CONTEXT)
        self.assertIs(span.is_recording_events(), True)

    def test_meter(self):
        meter = metrics.Meter()
        metric = meter.create_metric("", "", "", float, metrics.Counter)
        self.assertNotIsInstance(metric, DefaultMetric)
