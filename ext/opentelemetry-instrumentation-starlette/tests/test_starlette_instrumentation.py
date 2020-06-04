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

import sys
import unittest
import unittest.mock as mock

import opentelemetry.instrumentation.starlette as otel_starlette
from opentelemetry.test.test_base import TestBase
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient


class TestStarletteApplication(TestBase):
    def setUp(self):
        super().setUp()
        self._app = self._create_instrumented_app()
        self._client = TestClient(self._app)

    def test_basic_starlette_call(self):
        response = self._client.get("/foobar")
        spans = self.memory_exporter.get_finished_spans()
        self.assertEquals(len(spans), 3)
        for span in spans:
            self.assertIn("foobar", span.name)

    @staticmethod
    def _create_instrumented_app():
        """Create an instrumented starlette application"""

        def home(request):
            return PlainTextResponse("hi")

        return otel_starlette._InstrumentedStarlette(
            routes=[Route("/foobar", home)]
        )
