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

import logging
import os
import subprocess
import time
import typing
import unittest

from pymongo import MongoClient

from opentelemetry import trace as trace_api
from opentelemetry.ext.pymongo import trace_integration
from opentelemetry.sdk.trace import Span, Tracer
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

MONGODB_HOST = os.getenv("MONGODB_HOST ", "localhost")
MONGODB_PORT = int(os.getenv("MONGODB_PORT ", "27017"))
MONGODB_DB_NAME = os.getenv("MONGODB_PORT ", "opentelemetry-tests")
MONGODB_COLLECTION_NAME = "test"


class TestFunctionalPymongo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        process = subprocess.run(
            "docker run -d -p 27017:27017 --name otmongo mongo", check=False
        )
        if process.returncode != 0:
            logging.warning("Failed to start MongoDB container")
        time.sleep(2)

        cls._tracer = Tracer()
        cls._span_exporter = InMemorySpanExporter()
        cls._span_processor = SimpleExportSpanProcessor(cls._span_exporter)
        cls._tracer.add_span_processor(cls._span_processor)
        trace_integration(cls._tracer)
        try:
            client = MongoClient(MONGODB_HOST, MONGODB_PORT)
            db = client[MONGODB_DB_NAME]
            cls._collection = db[MONGODB_COLLECTION_NAME]
        except Exception:  # noqa pylint: disable=broad-except
            logging.warning("Failed to connect to MongoDB")

    @classmethod
    def tearDownClass(cls):
        subprocess.run("docker stop otmongo", check=False)
        subprocess.run("docker rm otmongo", check=False)

    def setUp(self):
        self._span_exporter.clear()

    def validate_spans(self, spans: typing.Tuple[Span]):
        self.assertEqual(len(spans), 2)
        for span in spans:
            if span.name == "rootSpan":
                root_span = span
            else:
                pymongo_span = span
            self.assertIsInstance(span.start_time, int)
            self.assertIsInstance(span.end_time, int)
        self.assertIsNotNone(pymongo_span.parent)
        self.assertEqual(pymongo_span.parent.name, root_span.name)
        self.assertIs(pymongo_span.kind, trace_api.SpanKind.CLIENT)
        self.assertEqual(
            pymongo_span.attributes["db.instance"], MONGODB_DB_NAME
        )
        self.assertEqual(
            pymongo_span.attributes["peer.hostname"], MONGODB_HOST
        )
        self.assertEqual(pymongo_span.attributes["peer.port"], MONGODB_PORT)

    def test_insert(self):
        """Should create a child span for insert
        """
        with self._tracer.start_as_current_span("rootSpan"):
            self._collection.insert_one(
                {"name": "testName", "value": "testValue"}
            )
        self.validate_spans(self._span_exporter.get_finished_spans())

    def test_update(self):
        """Should create a child span for update
        """
        with self._tracer.start_as_current_span("rootSpan"):
            self._collection.update_one(
                {"name": "testName"}, {"$set": {"value": "someOtherValue"}}
            )
        self.validate_spans(self._span_exporter.get_finished_spans())

    def test_find(self):
        """Should create a child span for find
        """
        with self._tracer.start_as_current_span("rootSpan"):
            self._collection.find_one()
        self.validate_spans(self._span_exporter.get_finished_spans())

    def test_delete(self):
        """Should create a child span for delete
        """
        with self._tracer.start_as_current_span("rootSpan"):
            self._collection.delete_one({"name": "testName"})
        self.validate_spans(self._span_exporter.get_finished_spans())
