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

import os
import time
import unittest

import pymysql as pymy

from opentelemetry import trace as trace_api
from opentelemetry.ext.pymysql import trace_integration
from opentelemetry.sdk.trace import Tracer, TracerProvider
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

MYSQL_USER = os.getenv("MYSQL_USER ", "testuser")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD ", "testpassword")
MYSQL_HOST = os.getenv("MYSQL_HOST ", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT ", "3306"))
MYSQL_DB_NAME = os.getenv("MYSQL_DB_NAME ", "opentelemetry-tests")


class TestFunctionalPyMysql(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._connection = None
        cls._cursor = None
        cls._tracer_provider = TracerProvider()
        cls._tracer = Tracer(cls._tracer_provider, None)
        cls._span_exporter = InMemorySpanExporter()
        cls._span_processor = SimpleExportSpanProcessor(cls._span_exporter)
        cls._tracer_provider.add_span_processor(cls._span_processor)
        trace_integration(cls._tracer_provider)
        cls._connection = pymy.connect(
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            database=MYSQL_DB_NAME,
        )
        cls._cursor = cls._connection.cursor()

    @classmethod
    def tearDownClass(cls):
        if cls._connection:
            cls._connection.close()

    def setUp(self):
        self._span_exporter.clear()

    def validate_spans(self):
        spans = self._span_exporter.get_finished_spans()
        self.assertEqual(len(spans), 2)
        for span in spans:
            if span.name == "rootSpan":
                root_span = span
            else:
                db_span = span
            self.assertIsInstance(span.start_time, int)
            self.assertIsInstance(span.end_time, int)
        self.assertIsNotNone(root_span)
        self.assertIsNotNone(db_span)
        self.assertEqual(root_span.name, "rootSpan")
        self.assertEqual(db_span.name, "mysql.opentelemetry-tests")
        self.assertIsNotNone(db_span.parent)
        self.assertIs(db_span.parent, root_span.get_context())
        self.assertIs(db_span.kind, trace_api.SpanKind.CLIENT)
        self.assertEqual(db_span.attributes["db.instance"], MYSQL_DB_NAME)
        self.assertEqual(db_span.attributes["net.peer.name"], MYSQL_HOST)
        self.assertEqual(db_span.attributes["net.peer.port"], MYSQL_PORT)

    def test_execute(self):
        """Should create a child span for execute
        """
        with self._tracer.start_as_current_span("rootSpan"):
            self._cursor.execute("CREATE TABLE IF NOT EXISTS test (id INT)")
        self.validate_spans()

    def test_executemany(self):
        """Should create a child span for executemany
        """
        with self._tracer.start_as_current_span("rootSpan"):
            data = ["1", "2", "3"]
            stmt = "INSERT INTO test (id) VALUES (%s)"
            self._cursor.executemany(stmt, data)
        self.validate_spans()

    def test_callproc(self):
        """Should create a child span for callproc
        """
        with self._tracer.start_as_current_span("rootSpan"), self.assertRaises(
            Exception
        ):
            self._cursor.callproc("test", ())
            self.validate_spans()
