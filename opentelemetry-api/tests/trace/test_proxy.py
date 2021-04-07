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

import unittest

from opentelemetry import trace
from opentelemetry.trace.span import INVALID_SPAN_CONTEXT, NonRecordingSpan


class TestProvider(trace._DefaultTracerProvider):
    def get_tracer(
        self, instrumentation_module_name, instrumentaiton_library_version=None
    ):
        return TestTracer()


class TestTracer(trace._DefaultTracer):
    def start_span(self, *args, **kwargs):
        return TestSpan(INVALID_SPAN_CONTEXT)


class TestSpan(NonRecordingSpan):
    pass


class TestProxy(unittest.TestCase):
    def test_proxy_tracer(self):
        original_provider = trace._TRACER_PROVIDER

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

        # tracer provider now returns real instance
        self.assertIsInstance(trace.get_tracer_provider(), TestProvider)

        # references to the old provider still work but return real tracer now
        real_tracer = provider.get_tracer("proxy-test")
        self.assertIsInstance(real_tracer, TestTracer)

        # reference to old proxy tracer now delegates to a real tracer and
        # creates real spans
        with tracer.start_span("") as span:
            self.assertIsInstance(span, TestSpan)

        trace._TRACER_PROVIDER = original_provider
