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

from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerProvider, export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


class TestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tracer_provider = TracerProvider()
        trace_api.set_tracer_provider(cls.tracer_provider)
        cls.memory_exporter = InMemorySpanExporter()
        span_processor = export.SimpleExportSpanProcessor(cls.memory_exporter)
        cls.tracer_provider.add_span_processor(span_processor)

    @classmethod
    def tearDownClass(cls):
        from opentelemetry import trace as trace_api

    def setUp(self):
        self.memory_exporter.clear()
