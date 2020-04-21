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

from opentelemetry.ext.mysql import trace_integration
from opentelemetry.test.test_base import TestBase


class TestMysqlIntegration(TestBase):
    def test_trace_integration(self):
        tracer = self.tracer_provider.get_tracer(__name__)

        with mock.patch("mysql.connector.connect") as mock_connect:
            mock_connect.get.side_effect = mysql.connector.MySQLConnection()
            trace_integration(tracer)
            cnx = mysql.connector.connect(database="test")
            cursor = cnx.cursor()
            query = "SELECT * FROM test"
            cursor.execute(query)
            spans_list = self.memory_exporter.get_finished_spans()
            self.assertEqual(len(spans_list), 1)
