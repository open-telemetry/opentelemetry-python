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
import typing
import unittest

from pymongo import MongoClient

from opentelemetry import trace as trace_api
from opentelemetry.ext.pymongo import trace_integration
from opentelemetry.sdk.trace import Span, Tracer, TracerProvider
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

MONGODB_HOST = os.getenv("MONGODB_HOST ", "localhost")
MONGODB_PORT = int(os.getenv("MONGODB_PORT ", "27017"))
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME ", "opentelemetry-tests")
MONGODB_COLLECTION_NAME = "test"


class TestFunctionalPymongo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tracer_provider = TracerProvider()
        cls._tracer = Tracer(cls._tracer_provider, None)
        cls._span_exporter = InMemorySpanExporter()
        cls._span_processor = SimpleExportSpanProcessor(cls._span_exporter)
        cls._tracer_provider.add_span_processor(cls._span_processor)
        trace_integration(cls._tracer)
        client = MongoClient(
            MONGODB_HOST, MONGODB_PORT, serverSelectionTimeoutMS=2000
        )
        db = client[MONGODB_DB_NAME]
        cls._collection = db[MONGODB_COLLECTION_NAME]

    def setUp(self):
        self._span_exporter.clear()

    def validate_spans(self):
        spans = self._span_exporter.get_finished_spans()
        self.assertEqual(len(spans), 2)
        for span in spans:
            if span.name == "rootSpan":
                root_span = span
            else:
                pymongo_span = span
            self.assertIsInstance(span.start_time, int)
            self.assertIsInstance(span.end_time, int)
        self.assertIsNot(root_span, None)
        self.assertIsNot(pymongo_span, None)
        self.assertIsNotNone(pymongo_span.parent)
        self.assertEqual(pymongo_span.parent.name, root_span.name)
        self.assertIs(pymongo_span.kind, trace_api.SpanKind.CLIENT)
        self.assertEqual(
            pymongo_span.attributes["db.instance"], MONGODB_DB_NAME
        )
        self.assertEqual(
            pymongo_span.attributes["net.peer.name"], MONGODB_HOST
        )
        self.assertEqual(
            pymongo_span.attributes["net.peer.port"], MONGODB_PORT
        )

    def test_insert(self):
        """Should create a child span for insert
        """
        with self._tracer.start_as_current_span("rootSpan"):
            self._collection.insert_one(
                {"name": "testName", "value": "testValue"}
            )
        self.validate_spans()

    def test_update(self):
        """Should create a child span for update
        """
        with self._tracer.start_as_current_span("rootSpan"):
            self._collection.update_one(
                {"name": "testName"}, {"$set": {"value": "someOtherValue"}}
            )
        self.validate_spans()

    def test_find(self):
        """Should create a child span for find
        """
        with self._tracer.start_as_current_span("rootSpan"):
            self._collection.find_one()
        self.validate_spans()

    def test_delete(self):
        """Should create a child span for delete
        """
        with self._tracer.start_as_current_span("rootSpan"):
            self._collection.delete_one({"name": "testName"})
        self.validate_spans()
