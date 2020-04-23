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

from unittest import mock

import mysql.connector

import opentelemetry.ext.mysql
from opentelemetry.sdk import resources
from opentelemetry.test.test_base import TestBase


class TestMysqlIntegration(TestBase):
    def test_trace_integration(self):
        with mock.patch("mysql.connector.connect") as mock_connect:
            mock_connect.get.side_effect = mysql.connector.MySQLConnection()
            opentelemetry.ext.mysql.trace_integration()
            cnx = mysql.connector.connect(database="test")
            cursor = cnx.cursor()
            query = "SELECT * FROM test"
            cursor.execute(query)

        spans_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans_list), 1)
        span = spans_list[0]

        # Check version and name in span's instrumentation info
        self.check_span_instrumentation_info(span, opentelemetry.ext.mysql)

    def test_custom_tracer_provider(self):
        resource = resources.Resource.create({})
        result = self.create_tracer_provider(resource=resource)
        tracer_provider, exporter = result

        with mock.patch("mysql.connector.connect") as mock_connect:
            mock_connect.get.side_effect = mysql.connector.MySQLConnection()
            opentelemetry.ext.mysql.trace_integration(tracer_provider)
            cnx = mysql.connector.connect(database="test")
            cursor = cnx.cursor()
            query = "SELECT * FROM test"
            cursor.execute(query)

        span_list = exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
        span = span_list[0]

        self.assertIs(span.resource, resource)
