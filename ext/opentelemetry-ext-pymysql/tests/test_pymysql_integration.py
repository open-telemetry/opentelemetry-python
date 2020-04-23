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

import pymysql

import opentelemetry.ext.pymysql
from opentelemetry.ext.pymysql import PymysqlInstrumentor
from opentelemetry.test.test_base import TestBase


class TestPyMysqlIntegration(TestBase):
    @mock.patch("pymysql.connect")
    # pylint: disable=unused-argument
    def test_instrumentor(self, mock_connect):
        PymysqlInstrumentor().instrument()

        cnx = pymysql.connect(database="test")
        cursor = cnx.cursor()
        query = "SELECT * FROM test"
        cursor.execute(query)

        spans_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans_list), 1)
        span = spans_list[0]

        # Check version and name in span's instrumentation info
        self.check_span_instrumentation_info(span, opentelemetry.ext.pymysql)

        # check that no spans are generated ater uninstrument
        PymysqlInstrumentor().uninstrument()

        cnx = pymysql.connect(database="test")
        cursor = cnx.cursor()
        query = "SELECT * FROM test"
        cursor.execute(query)

        spans_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans_list), 1)
