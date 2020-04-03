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

import os
import time
import unittest

import psycopg2

from opentelemetry import trace as trace_api
from opentelemetry.ext.psycopg2 import trace_integration
from opentelemetry.sdk.trace import Tracer, TracerProvider
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

POSTGRES_HOST = os.getenv("POSTGRESQL_HOST ", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRESQL_PORT ", "5432"))
POSTGRES_DB_NAME = os.getenv("POSTGRESQL_DB_NAME ", "opentelemetry-tests")
POSTGRES_PASSWORD = os.getenv("POSTGRESQL_HOST ", "testpassword")
POSTGRES_USER = os.getenv("POSTGRESQL_HOST ", "testuser")


class TestFunctionalPsycopg(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._connection = None
        cls._cursor = None
        cls._tracer_provider = TracerProvider()
        cls._tracer = Tracer(cls._tracer_provider, None)
        cls._span_exporter = InMemorySpanExporter()
        cls._span_processor = SimpleExportSpanProcessor(cls._span_exporter)
        cls._tracer_provider.add_span_processor(cls._span_processor)
        trace_integration(cls._tracer)
        cls._connection = psycopg2.connect(
            dbname=POSTGRES_DB_NAME,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
        )
        cls._connection.set_session(autocommit=True)
        cls._cursor = cls._connection.cursor()

    @classmethod
    def tearDownClass(cls):
        if cls._cursor:
            cls._cursor.close()
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
                child_span = span
            self.assertIsInstance(span.start_time, int)
            self.assertIsInstance(span.end_time, int)
        self.assertIsNotNone(root_span)
        self.assertIsNotNone(child_span)
        self.assertEqual(root_span.name, "rootSpan")
        self.assertEqual(child_span.name, "postgresql.opentelemetry-tests")
        self.assertIsNotNone(child_span.parent)
        self.assertEqual(child_span.parent.name, root_span.name)
        self.assertIs(child_span.kind, trace_api.SpanKind.CLIENT)
        self.assertEqual(
            child_span.attributes["db.instance"], POSTGRES_DB_NAME
        )
        self.assertEqual(child_span.attributes["net.peer.name"], POSTGRES_HOST)
        self.assertEqual(child_span.attributes["net.peer.port"], POSTGRES_PORT)

    def test_execute(self):
        """Should create a child span for execute method
        """
        with self._tracer.start_as_current_span("rootSpan"):
            self._cursor.execute(
                "CREATE TABLE IF NOT EXISTS test (id integer)"
            )
        self.validate_spans()

    def test_executemany(self):
        """Should create a child span for executemany
        """
        with self._tracer.start_as_current_span("rootSpan"):
            data = ("1", "2", "3")
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
