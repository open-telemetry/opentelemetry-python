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


class RecordingSpan(trace.Span):
    def __init__(self, context: trace.SpanContext) -> None:
        self._context = context

    def get_span_context(self) -> trace.SpanContext:
        return self._context

    def is_recording(self) -> bool:
        return True

    def end(self, end_time=None) -> None:
        pass

    def set_attributes(self, attributes) -> None:
        pass

    def set_attribute(self, key, value) -> None:
        pass

    def add_event(
        self,
        name: str,
        attributes=None,
        timestamp=None,
    ) -> None:
        pass

    def add_link(
        self,
        context,
        attributes=None,
    ) -> None:
        pass

    def update_name(self, name) -> None:
        pass

    def set_status(
        self,
        status,
        description=None,
    ) -> None:
        pass

    def record_exception(
        self,
        exception,
        attributes=None,
        timestamp=None,
        escaped=False,
    ) -> None:
        pass

    def __repr__(self) -> str:
        return f"RecordingSpan({self._context!r})"


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
            self.assertFalse(span.get_span_context().is_valid)
            self.assertIs(span.is_recording(), False)
            with tracer.start_span("test2") as span2:
                self.assertFalse(span2.get_span_context().is_valid)
                self.assertIs(span2.is_recording(), False)

    def test_default_tracer_context_propagation_recording_span(self):
        tracer_provider = trace.NoOpTracerProvider()
        tracer = tracer_provider.get_tracer(__name__)
        span_context = trace.SpanContext(
            2604504634922341076776623263868986797,
            5213367945872657620,
            False,
            trace.TraceFlags(0x01),
        )
        ctx = trace.set_span_in_context(RecordingSpan(context=span_context))
        with tracer.start_span("test", context=ctx) as span:
            self.assertTrue(span.get_span_context().is_valid)
            self.assertEqual(span.get_span_context(), span_context)
            self.assertIs(span.is_recording(), False)

    def test_default_tracer_context_propagation_non_recording_span(self):
        tracer_provider = trace.NoOpTracerProvider()
        tracer = tracer_provider.get_tracer(__name__)
        ctx = trace.set_span_in_context(trace.INVALID_SPAN)
        with tracer.start_span("test", context=ctx) as span:
            self.assertFalse(span.get_span_context().is_valid)
            self.assertIs(span, trace.INVALID_SPAN)

    def test_default_tracer_context_propagation_with_invalid_context(self):
        tracer_provider = trace.NoOpTracerProvider()
        tracer = tracer_provider.get_tracer(__name__)
        ctx = trace.set_span_in_context(
            RecordingSpan(context="invalid_context")  # type: ignore[reportArgumentType]
        )
        with self.assertRaises(TypeError):
            tracer.start_span("test", context=ctx)

    def test_span(self):
        with self.assertRaises(TypeError):
            # pylint: disable=abstract-class-instantiated
            trace.Span()  # type:ignore

    def test_default_span(self):
        span = trace.NonRecordingSpan(trace.INVALID_SPAN_CONTEXT)
        self.assertEqual(span.get_span_context(), trace.INVALID_SPAN_CONTEXT)
        self.assertIs(span.is_recording(), False)
