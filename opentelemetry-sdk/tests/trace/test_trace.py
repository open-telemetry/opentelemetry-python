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

from opentelemetry import trace as trace_api
from opentelemetry.sdk import trace


class TestTracer(unittest.TestCase):

    def test_extends_api(self):
        tracer = trace.Tracer()
        self.assertIsInstance(tracer, trace_api.Tracer)


class TestSpan(unittest.TestCase):

    def test_basic_span(self):
        span = trace.Span('name')
        self.assertEqual(span.name, 'name')
