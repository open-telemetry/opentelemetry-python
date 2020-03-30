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

import psycopg2

from opentelemetry import trace as trace_api
from opentelemetry.ext.psycopg2 import trace_integration


class TestPostgresqlIntegration(unittest.TestCase):
    def test_trace_integration(self):
        tracer = trace_api.DefaultTracer()
        with mock.patch("psycopg2.connect"):
            trace_integration(tracer)
            cnx = psycopg2.connect(database="test")
            self.assertIsNotNone(cnx.cursor_factory)
