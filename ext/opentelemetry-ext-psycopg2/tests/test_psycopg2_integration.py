# Copyright 2020, OpenTelemetry Authors
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
        tracer = trace_api.Tracer()
        span = mock.create_autospec(trace_api.Span, spec_set=True)
        start_current_span_patcher = mock.patch.object(
            tracer,
            "start_as_current_span",
            autospec=True,
            spec_set=True,
            return_value=span,
        )
        start_as_current_span = start_current_span_patcher.start()
        trace_integration(tracer)

        conn = psycopg2.connect("dbname=testdb user=postgres password=passwordPostgres")
        cur = conn.cursor()
        cur.execute("SELECT * FROM testtable;")
        cur.fetchone()
    
