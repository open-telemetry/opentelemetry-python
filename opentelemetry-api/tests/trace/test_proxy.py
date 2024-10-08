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

# pylint: disable=W0212,W0222,W0221
import typing
import unittest

from opentelemetry import trace
from opentelemetry.test.globals_test import TraceGlobalsTest
from opentelemetry.trace.span import (
    INVALID_SPAN_CONTEXT,
    NonRecordingSpan,
    Span,
)
from opentelemetry.util._decorator import _agnosticcontextmanager
from opentelemetry.util.types import Attributes


class TestProvider(trace.NoOpTracerProvider):
    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: typing.Optional[str] = None,
        schema_url: typing.Optional[str] = None,
        attributes: typing.Optional[Attributes] = None,
    ) -> trace.Tracer:
        return TestTracer()


class TestTracer(trace.NoOpTracer):
    def start_span(self, *args, **kwargs):
        return SpanTest(INVALID_SPAN_CONTEXT)

    @_agnosticcontextmanager  # pylint: disable=protected-access
    def start_as_current_span(self, *args, **kwargs):  # type: ignore
        with trace.use_span(self.start_span(*args, **kwargs)) as span:  # type: ignore
            yield span


class SpanTest(NonRecordingSpan):
    pass


class TestProxy(TraceGlobalsTest, unittest.TestCase):
    def test_proxy_tracer(self):
        provider = trace.get_tracer_provider()
        # proxy provider
        self.assertIsInstance(provider, trace.ProxyTracerProvider)

        # provider returns proxy tracer
        tracer = provider.get_tracer("proxy-test")
        self.assertIsInstance(tracer, trace.ProxyTracer)

        with tracer.start_span("span1") as span:
            self.assertIsInstance(span, trace.NonRecordingSpan)

        with tracer.start_as_current_span("span2") as span:
            self.assertIsInstance(span, trace.NonRecordingSpan)

        # set a real provider
        trace.set_tracer_provider(TestProvider())

        # get_tracer_provider() now returns the real provider
        self.assertIsInstance(trace.get_tracer_provider(), TestProvider)

        # tracer provider now returns real instance
        self.assertIsInstance(trace.get_tracer_provider(), TestProvider)

        # references to the old provider still work but return real tracer now
        real_tracer = provider.get_tracer("proxy-test")
        self.assertIsInstance(real_tracer, TestTracer)

        # reference to old proxy tracer now delegates to a real tracer and
        # creates real spans
        with tracer.start_span("") as span:
            self.assertIsInstance(span, SpanTest)

    def test_late_config(self):
        # get a tracer and instrument a function as we would at the
        # root of a module
        tracer = trace.get_tracer("test")

        @tracer.start_as_current_span("span")
        def my_function() -> Span:
            return trace.get_current_span()

        # call function before configuring tracing provider, should
        # return INVALID_SPAN from the NoOpTracer
        self.assertEqual(my_function(), trace.INVALID_SPAN)

        # configure tracing provider
        trace.set_tracer_provider(TestProvider())
        # call function again, we should now be getting a TestSpan
        self.assertIsInstance(my_function(), SpanTest)
