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

from opentelemetry import trace
from opentelemetry.sdk.trace import Tracer as OTelTracer
from opentracing import Tracer, Scope, Span

import opentracingshim

class TestShim(unittest.TestCase):
    def setUp(self):
        self.tracer = trace.tracer()
        self.ot_tracer = opentracingshim.create_tracer(self.tracer)

    @classmethod
    def setUpClass(cls):
        """Set preferred tracer implementation only once rather than before
        every test method.
        """
        # TODO: Do we need to call setUpClass() on super()?
        # Seems to work fine without it.
        super(TestShim, cls).setUpClass()
        trace.set_preferred_tracer_implementation(lambda T: OTelTracer())

    def test_basic(self):
        # Verify shim is an OpenTracing tracer.
        self.assertIsInstance(self.ot_tracer, Tracer)

        with self.ot_tracer.start_active_span("TestBasic") as scope:
            self.assertIsInstance(scope, Scope)
            self.assertIsInstance(scope.span, Span)

    def test_set_tag(self):
        with self.ot_tracer.start_active_span("TestSetTag") as scope:
            scope.span.set_tag("my", "tag")
