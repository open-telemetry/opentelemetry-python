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
from opentelemetry.ext.pymongo import CommandTracer, trace_integration
from opentelemetry.util import time_ns


class TestPymongoIntegration(unittest.TestCase):
    def test_trace_integration(self):
        mock_register = mock.Mock()
        patch = mock.patch(
            "pymongo.monitoring.register", side_effect=mock_register
        )
        mock_tracer = MockTracer()
        with patch:
            trace_integration(mock_tracer)

        self.assertTrue(mock_register.called)

    def test_started(self):
        command_attrs = {
            "filter": "filter",
            "sort": "sort",
            "limit": "limit",
            "pipeline": "pipeline",
            "command_name": "find",
        }
        mock_tracer = MockTracer()
        command_tracer = CommandTracer(mock_tracer)
        mock_event = MockEvent(
            command_attrs, ("test.com", "1234"), "test_request_id"
        )
        command_tracer.started(event=mock_event)
        # pylint: disable=protected-access
        span = command_tracer._get_span(mock_event)
        self.assertIs(span.kind, trace_api.SpanKind.CLIENT)
        self.assertEqual(span.name, "mongodb.command_name.find")
        self.assertEqual(span.attributes["component"], "mongodb")
        self.assertEqual(span.attributes["db.type"], "mongodb")
        self.assertEqual(span.attributes["db.instance"], "database_name")
        self.assertEqual(span.attributes["db.statement"], "command_name find")
        self.assertEqual(span.attributes["peer.hostname"], "test.com")
        self.assertEqual(span.attributes["peer.port"], "1234")
        self.assertEqual(
            span.attributes["db.mongo.operation_id"], "operation_id"
        )
        self.assertEqual(
            span.attributes["db.mongo.request_id"], "test_request_id"
        )

        self.assertEqual(span.attributes["db.mongo.filter"], "filter")
        self.assertEqual(span.attributes["db.mongo.sort"], "sort")
        self.assertEqual(span.attributes["db.mongo.limit"], "limit")
        self.assertEqual(span.attributes["db.mongo.pipeline"], "pipeline")

    def test_succeeded(self):
        mock_tracer = MockTracer()
        mock_event = MockEvent({})
        command_tracer = CommandTracer(mock_tracer)
        command_tracer.started(event=mock_event)
        # pylint: disable=protected-access
        span = command_tracer._get_span(mock_event)
        command_tracer.succeeded(event=mock_event)
        self.assertEqual(
            span.attributes["db.mongo.duration_micros"], "duration_micros"
        )
        self.assertIs(
            span.status.canonical_code, trace_api.status.StatusCanonicalCode.OK
        )
        self.assertEqual(span.status.description, "reply")
        self.assertIsNotNone(span.end_time)

    def test_failed(self):
        mock_tracer = MockTracer()
        mock_event = MockEvent({})
        command_tracer = CommandTracer(mock_tracer)
        command_tracer.started(event=mock_event)
        # pylint: disable=protected-access
        span = command_tracer._get_span(mock_event)
        command_tracer.failed(event=mock_event)
        self.assertEqual(
            span.attributes["db.mongo.duration_micros"], "duration_micros"
        )
        self.assertIs(
            span.status.canonical_code,
            trace_api.status.StatusCanonicalCode.UNKNOWN,
        )
        self.assertEqual(span.status.description, "failure")
        self.assertIsNotNone(span.end_time)

    def test_multiple_commands(self):
        mock_tracer = MockTracer()
        first_mock_event = MockEvent({}, ("firstUrl", "123"), "first")
        second_mock_event = MockEvent({}, ("secondUrl", "456"), "second")
        command_tracer = CommandTracer(mock_tracer)
        command_tracer.started(event=first_mock_event)
        # pylint: disable=protected-access
        first_span = command_tracer._get_span(first_mock_event)
        command_tracer.started(event=second_mock_event)
        # pylint: disable=protected-access
        second_span = command_tracer._get_span(second_mock_event)
        command_tracer.succeeded(event=first_mock_event)
        command_tracer.failed(event=second_mock_event)

        self.assertEqual(first_span.attributes["db.mongo.request_id"], "first")
        self.assertIs(
            first_span.status.canonical_code,
            trace_api.status.StatusCanonicalCode.OK,
        )
        self.assertEqual(
            second_span.attributes["db.mongo.request_id"], "second"
        )
        self.assertIs(
            second_span.status.canonical_code,
            trace_api.status.StatusCanonicalCode.UNKNOWN,
        )


class MockCommand:
    def __init__(self, command_attrs):
        self.command_attrs = command_attrs

    def get(self, key, default=""):
        return self.command_attrs.get(key, default)


class MockEvent:
    def __init__(self, command_attrs, connection_id=None, request_id=""):
        self.command = MockCommand(command_attrs)
        self.connection_id = connection_id
        self.request_id = request_id

    def __getattr__(self, item):
        return item


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
        self.end_span = mock.Mock()

    # pylint: disable=no-self-use
    def start_span(self, name, kind):
        span = MockSpan()
        span.attributes = {}
        span.status = None
        span.name = name
        span.kind = kind
        return span
