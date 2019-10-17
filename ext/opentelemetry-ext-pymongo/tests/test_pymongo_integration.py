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

from opentelemetry.ext.pymongo import trace_integration, CommandTracer


class TestPymongoIntegration(unittest.TestCase):

    def test_trace_integration(self):
        mock_register = mock.Mock()

        patch = mock.patch(
            'pymongo.monitoring.register',
            side_effect=mock_register)

        with patch:
            trace_integration()

        self.assertTrue(mock_register.called)

    def test_started(self):
        mock_tracer = MockTracer()

        patch = mock.patch(
            'opencensus.trace.execution_context.get_opencensus_tracer',
            return_value=mock_tracer)

        command_attrs = {
            'filter': 'filter',
            'sort': 'sort',
            'limit': 'limit',
            'pipeline': 'pipeline',
            'command_name': 'find'
        }

        expected_attrs = {
            'component': 'mongodb',
            'db.type': 'mongodb',
            'db.instance': 'database_name',
            'db.statement': 'find',
            'filter': 'filter',
            'sort': 'sort',
            'limit': 'limit',
            'pipeline': 'pipeline',
            'request_id': 'request_id',
            'connection_id': 'connection_id'
        }

        expected_name = 'pymongo.database_name.find.command_name'

        with patch:
            CommandTracer().started(
                event=MockEvent(command_attrs))

        self.assertEqual(mock_tracer.span.attributes, expected_attrs)
        self.assertEqual(mock_tracer.span.name, expected_name)

    def test_succeed(self):
        mock_tracer = MockTracer()
        mock_tracer.start_span()

        patch = mock.patch(
            'opencensus.trace.execution_context.get_opencensus_tracer',
            return_value=mock_tracer)

        expected_status = {
            'code': 0,
            'message': '',
            'details': None
        }

        with patch:
            CommandTracer().succeeded(event=MockEvent(None))

        self.assertEqual(mock_tracer.span.status, expected_status)
        mock_tracer.end_span.assert_called_with()

    def test_failed(self):
        mock_tracer = MockTracer()
        mock_tracer.start_span()

        patch = mock.patch(
            'opencensus.trace.execution_context.get_opencensus_tracer',
            return_value=mock_tracer)

        expected_status = {
            'code': 2,
            'message': 'MongoDB error',
            'details': 'failure'
        }

        with patch:
            CommandTracer().failed(event=MockEvent(None))

        self.assertEqual(mock_tracer.span.status, expected_status)
        mock_tracer.end_span.assert_called_with()


class MockCommand(object):
    def __init__(self, command_attrs):
        self.command_attrs = command_attrs

    def get(self, key):
        return self.command_attrs.get(key)


class MockEvent(object):
    def __init__(self, command_attrs):
        self.command = MockCommand(command_attrs)

    def __getattr__(self, item):
        return item


class MockSpan(object):
    def __init__(self):
        self.status = None

    def set_status(self, status):
        self.status = {
            'code': status.canonical_code,
            'message': status.description,
            'details': status.details,
        }


class MockTracer(object):
    def __init__(self):
        self.span = MockSpan()
        self.end_span = mock.Mock()

    def start_span(self, name=None):
        self.span.name = name
        self.span.attributes = {}
        self.span.status = {}
        return self.span

    def add_attribute_to_current_span(self, key, value):
        self.span.attributes[key] = value

    def get_current_span(self):
        return self.span
