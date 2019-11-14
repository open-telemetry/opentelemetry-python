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

from opentelemetry import trace as trace_api
from opentelemetry.ext.dbapi import DatabaseApiTracer


class TestMysqlIntegration(unittest.TestCase):
    def setUp(self):
        self.tracer = trace_api.tracer()
        self.span = MockSpan()
        self.start_current_span_patcher = mock.patch.object(
            self.tracer,
            "start_as_current_span",
            autospec=True,
            spec_set=True,
            return_value=self.span,
        )

        self.start_as_current_span = self.start_current_span_patcher.start()

    def tearDown(self):
        self.start_current_span_patcher.stop()

    def test_span_succeeded(self):
        connection_props = {
            "database": "testdatabase",
            "server_host": "testhost",
            "server_port": 123,
            "user": "testuser",
        }
        mysql_tracer = DatabaseApiTracer(
            self.tracer, "testcomponent", "testtype"
        )
        mock_connection = mysql_tracer.wrap_connect(
            mock_connect, {}, connection_props
        )
        cursor = mock_connection.cursor()
        cursor.execute("Test query", ("param1Value", False))
        self.assertTrue(self.start_as_current_span.called)
        self.assertEqual(
            self.start_as_current_span.call_args[0][0],
            "testcomponent.testdatabase",
        )
        self.assertIs(
            self.start_as_current_span.call_args[1]["kind"],
            trace_api.SpanKind.CLIENT,
        )
        self.assertEqual(self.span.attributes["component"], "testcomponent")
        self.assertEqual(self.span.attributes["db.type"], "testtype")
        self.assertEqual(self.span.attributes["db.instance"], "testdatabase")
        self.assertEqual(
            self.span.attributes["db.statement"],
            "Test query params=('param1Value', False)",
        )
        self.assertEqual(self.span.attributes["db.user"], "testuser")
        self.assertEqual(self.span.attributes["peer.hostname"], "testhost")
        self.assertEqual(self.span.attributes["peer.port"], 123)
        self.assertIs(
            self.span.status.canonical_code,
            trace_api.status.StatusCanonicalCode.OK,
        )

    def test_span_failed(self):
        mysql_tracer = DatabaseApiTracer(self.tracer, "testcomponent")
        mock_connection = mysql_tracer.wrap_connect(mock_connect, {}, {})
        cursor = mock_connection.cursor()
        cursor.execute("Test query", throw_exception=True)

        self.assertEqual(self.span.attributes["db.statement"], "Test query")
        self.assertIs(
            self.span.status.canonical_code,
            trace_api.status.StatusCanonicalCode.UNKNOWN,
        )
        self.assertEqual(self.span.status.description, "Test Exception")

    def test_executemany(self):
        mysql_tracer = DatabaseApiTracer(self.tracer, "testcomponent")
        mock_connection = mysql_tracer.wrap_connect(mock_connect, {}, {})
        cursor = mock_connection.cursor()
        cursor.executemany("Test query")
        self.assertTrue(self.start_as_current_span.called)
        self.assertEqual(self.span.attributes["db.statement"], "Test query")

    def test_callproc(self):
        mysql_tracer = DatabaseApiTracer(self.tracer, "testcomponent")
        mock_connection = mysql_tracer.wrap_connect(mock_connect, {}, {})
        cursor = mock_connection.cursor()
        cursor.callproc("Test stored procedure")
        self.assertTrue(self.start_as_current_span.called)
        self.assertEqual(
            self.span.attributes["db.statement"], "Test stored procedure"
        )


# pylint: disable=unused-argument
def mock_connect(*args, **kwargs):
    database = kwargs.get("database")
    server_host = kwargs.get("server_host")
    server_port = kwargs.get("server_port")
    user = kwargs.get("user")
    return MockMySqlConnection(database, server_port, server_host, user)


class MockMySqlConnection:
    def __init__(self, database, server_port, server_host, user):
        self.database = database
        self.server_port = server_port
        self.server_host = server_host
        self.user = user

    # pylint: disable=no-self-use
    def cursor(self):
        return MockMySqlCursor()


class MockMySqlCursor:
    # pylint: disable=unused-argument, no-self-use
    def execute(self, query, params=None, throw_exception=False):
        if throw_exception:
            raise Exception("Test Exception")

    # pylint: disable=unused-argument, no-self-use
    def executemany(self, query, params=None, throw_exception=False):
        if throw_exception:
            raise Exception("Test Exception")

    # pylint: disable=unused-argument, no-self-use
    def callproc(self, query, params=None, throw_exception=False):
        if throw_exception:
            raise Exception("Test Exception")


class MockSpan:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def __init__(self):
        self.status = None
        self.name = ""
        self.kind = trace_api.SpanKind.INTERNAL
        self.attributes = {}

    def set_attribute(self, key, value):
        self.attributes[key] = value

    def set_status(self, status):
        self.status = status
