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
from unittest import mock

from opentelemetry import metrics, trace


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
        tracer_provider = trace.DefaultTracerProvider()
        tracer = tracer_provider.get_tracer(__name__)
        with tracer.start_span("test") as span:
            self.assertEqual(span.get_context(), trace.INVALID_SPAN_CONTEXT)
            self.assertEqual(span, trace.INVALID_SPAN)
            self.assertIs(span.is_recording_events(), False)
            with tracer.start_span("test2") as span2:
                self.assertEqual(
                    span2.get_context(), trace.INVALID_SPAN_CONTEXT
                )
                self.assertEqual(span2, trace.INVALID_SPAN)
                self.assertIs(span2.is_recording_events(), False)

    def test_span(self):
        with self.assertRaises(TypeError):
            # pylint: disable=abstract-class-instantiated
            trace.Span()  # type:ignore

    def test_default_span(self):
        span = trace.DefaultSpan(trace.INVALID_SPAN_CONTEXT)
        self.assertEqual(span.get_context(), trace.INVALID_SPAN_CONTEXT)
        self.assertIs(span.is_recording_events(), False)

    # METER

    def test_meter(self):
        with self.assertRaises(TypeError):
            # pylint: disable=abstract-class-instantiated
            metrics.Meter()  # type:ignore

    def test_default_meter(self):
        meter_provider = metrics.DefaultMeterProvider()
        meter = meter_provider.get_meter(__name__)
        self.assertIsInstance(meter, metrics.DefaultMeter)

    # pylint: disable=no-self-use
    def test_record_batch(self):
        meter = metrics.DefaultMeter()
        counter = metrics.Counter()
        meter.record_batch({}, ((counter, 1),))

    def test_create_metric(self):
        meter = metrics.DefaultMeter()
        metric = meter.create_metric("", "", "", float, metrics.Counter)
        self.assertIsInstance(metric, metrics.DefaultMetric)

    def test_register_observer(self):
        meter = metrics.DefaultMeter()
        callback = mock.Mock()
        observer = meter.register_observer(
            callback, "", "", "", int, metrics.ValueObserver
        )
        self.assertIsInstance(observer, metrics.DefaultObserver)

    def test_unregister_observer(self):
        meter = metrics.DefaultMeter()
        observer = metrics.DefaultObserver()
        meter.unregister_observer(observer)
