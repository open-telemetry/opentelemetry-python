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
from opentelemetry.ext.mysql import MySqlTracer
from opentelemetry.util import time_ns


class TestMysqlIntegration(unittest.TestCase):
    def test_span_succeeded(self):
        mock_tracer = MockTracer()
        connection_props = {
            "database": "testdatabase",
            "server_host": "testhost",
            "server_port": 123,
            "user": "testuser",
        }
        mysql_tracer = MySqlTracer(mock_tracer)
        mock_connection = mysql_tracer.wrap_connect(
            mock_connect, {}, connection_props
        )
        cursor = mock_connection.cursor()
        cursor.execute(
            "Test query", ("param1Value", False)
        )
        span = mock_tracer.get_current_span()

        self.assertIs(span.kind, trace_api.SpanKind.CLIENT)
        self.assertEqual(span.name, "mysql.testdatabase")
        self.assertEqual(span.attributes["component"], "mysql")
        self.assertEqual(span.attributes["db.type"], "sql")
        self.assertEqual(span.attributes["db.instance"], "testdatabase")
        self.assertEqual(
            span.attributes["db.statement"],
            "Test query params=('param1Value', False)",
        )
        self.assertEqual(span.attributes["db.user"], "testuser")
        self.assertEqual(span.attributes["peer.hostname"], "testhost")
        self.assertEqual(span.attributes["peer.port"], 123)
        self.assertIs(
            span.status.canonical_code, trace_api.status.StatusCanonicalCode.OK
        )

    def test_span_failed(self):
        mock_tracer = MockTracer()
        mysql_tracer = MySqlTracer(mock_tracer)
        mock_connection = mysql_tracer.wrap_connect(mock_connect, {}, {})
        cursor = mock_connection.cursor()
        cursor.execute("Test query", throw_exception=True)
        span = mock_tracer.get_current_span()

        self.assertEqual(span.attributes["db.statement"], "Test query")
        self.assertIs(
            span.status.canonical_code,
            trace_api.status.StatusCanonicalCode.UNKNOWN,
        )
        self.assertEqual(span.status.description, "Test Exception")


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


class MockSpan:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def __init__(self):
        self.status = None
        self.name = ""
        self.kind = trace_api.SpanKind.INTERNAL
        self.attributes = None
        self.end_time = None

    def set_attribute(self, key, value):
        self.attributes[key] = value

    def set_status(self, status):
        self.status = status

    def end(self, end_time=None):
        self.end_time = end_time if end_time is not None else time_ns()


class MockTracer:
    def __init__(self):
        self.span = MockSpan()
        self.end_span = mock.Mock()
        self.span.attributes = {}
        self.span.status = None

    def start_current_span(self, name, kind):
        self.span.name = name
        self.span.kind = kind
        return self.span

    def get_current_span(self):
        return self.span
