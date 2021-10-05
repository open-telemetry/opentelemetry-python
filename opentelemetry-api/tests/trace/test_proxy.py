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
from opentelemetry.trace import (
    NoOpTracer,
    NoOpSpan,
    ProxyTracer,
    ProxyTracerProvider,
    get_tracer_provider,
    set_tracer_provider,
    NoOpTracerProvider,
)
from opentelemetry.trace.span import NonRecordingSpan


class TestProxy(unittest.TestCase):
    def test_proxy_tracer(self):
        original_provider = trace._TRACER_PROVIDER

        provider = get_tracer_provider()
        # proxy provider
        self.assertIsInstance(provider, ProxyTracerProvider)

        # provider returns proxy tracer
        tracer = provider.get_tracer("proxy-test")
        self.assertIsInstance(tracer, ProxyTracer)

        with tracer.start_span("span1") as span:
            self.assertIsInstance(span, NonRecordingSpan)

        with tracer.start_as_current_span("span2") as span:
            self.assertIsInstance(span, NonRecordingSpan)

        # set a real provider
        set_tracer_provider(NoOpTracerProvider())

        # tracer provider now returns real instance
        self.assertIsInstance(get_tracer_provider(), NoOpTracerProvider)

        # references to the old provider still work but return real tracer now
        real_tracer = provider.get_tracer("proxy-test")
        self.assertIsInstance(real_tracer, NoOpTracer)

        # reference to old proxy tracer now delegates to a real tracer and
        # creates real spans
        with tracer.start_span("") as span:
            self.assertIsInstance(span, NoOpSpan)

        trace._TRACER_PROVIDER = original_provider
