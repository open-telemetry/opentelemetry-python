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
from unittest import mock

import pymysql

from opentelemetry import trace as trace_api
from opentelemetry.ext.pymysql import trace_integration


class TestPyMysqlIntegration(unittest.TestCase):
    def test_trace_integration(self):
        tracer = trace_api.DefaultTracer()
        span = mock.create_autospec(trace_api.Span, spec_set=True)
        start_current_span_patcher = mock.patch.object(
            tracer,
            "start_as_current_span",
            autospec=True,
            spec_set=True,
            return_value=span,
        )
        start_as_current_span = start_current_span_patcher.start()

        with mock.patch("pymysql.connect"):
            trace_integration(tracer)
            cnx = pymysql.connect(database="test")
            cursor = cnx.cursor()
            query = "SELECT * FROM test"
            cursor.execute(query)
            self.assertTrue(start_as_current_span.called)
