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

import json
import logging
import unittest
import warnings
from unittest.mock import patch

from opentelemetry._logs.severity import SeverityNumber
from opentelemetry.attributes import BoundedAttributes
from opentelemetry.sdk import trace
from opentelemetry.sdk._logs import (
    LogData,
    LogDroppedAttributesWarning,
    LoggerProvider,
    LoggingHandler,
    LogLimits,
    LogRecord,
    LogRecordProcessor,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import (
    INVALID_SPAN,
    format_span_id,
    format_trace_id,
    set_span_in_context,
)


class TestLogRecord(unittest.TestCase):
    def test_serialized_context_none(self):
        record = LogRecord(context=None)
        self.assertEqual({}, record.serialized_context())

    def test_serialized_context_serializable(self):
        context = {
            "test-string": "value",
            "test-number": 42,
            "test-list": [1, 2, 3],
            "test-dict": {"key": "value"},
            "test-null": None,
            "test-bool": True,
        }
        record = LogRecord(context=context)
        self.assertEqual(context, record.serialized_context())

    def test_serialized_context_non_serializable(self):
        class MyTestObject:
            def __str__(self):
                return "foo-bar"

        context = {"test-string": "value", "test-object": MyTestObject()}
        record = LogRecord(context=context)
        expected = {"test-string": "value", "test-object": "foo-bar"}
        self.assertEqual(expected, record.serialized_context())

    def test_log_record_to_json(self):
        expected = json.dumps(
            {
                "body": "a log line",
                "severity_number": None,
                "severity_text": None,
                "attributes": {
                    "mapping": {"key": "value"},
                    "none": None,
                    "sequence": [1, 2],
                    "str": "string",
                },
                "dropped_attributes": 0,
                "timestamp": "1970-01-01T00:00:00.000000Z",
                "observed_timestamp": "1970-01-01T00:00:00.000000Z",
                "context": {},
                "trace_id": "",
                "span_id": "",
                "trace_flags": None,
                "resource": {
                    "attributes": {"service.name": "foo"},
                    "schema_url": "",
                },
            },
            indent=4,
        )
        actual = LogRecord(
            timestamp=0,
            observed_timestamp=0,
            body="a log line",
            resource=Resource({"service.name": "foo"}),
            attributes={
                "mapping": {"key": "value"},
                "none": None,
                "sequence": [1, 2],
                "str": "string",
            },
        )

        self.assertEqual(expected, actual.to_json(indent=4))
        self.assertEqual(
            actual.to_json(indent=None),
            '{"body": "a log line", "severity_number": null, "severity_text": null, "attributes": {"mapping": {"key": "value"}, "none": null, "sequence": [1, 2], "str": "string"}, "dropped_attributes": 0, "timestamp": "1970-01-01T00:00:00.000000Z", "observed_timestamp": "1970-01-01T00:00:00.000000Z", "context": {}, "trace_id": "", "span_id": "", "trace_flags": null, "resource": {"attributes": {"service.name": "foo"}, "schema_url": ""}}',
        )

    # pylint: disable=too-many-locals
    @patch("opentelemetry.sdk._logs._internal.get_current_span")
    @patch("opentelemetry.trace.propagation.set_value")
    @patch("opentelemetry.sdk.trace.RandomIdGenerator.generate_span_id")
    @patch("opentelemetry.sdk.trace.RandomIdGenerator.generate_trace_id")
    def test_log_record_to_json_with_span_correlation(
        self,
        mock_generate_trace_id,
        mock_generate_span_id,
        mock_set_value,
        mock_get_current_span,
    ):
        trace_id = 0x000000000000000000000000DEADBEEF
        span_id = 0x00000000DEADBEF0
        fixed_key = "current-span-test"

        mock_generate_trace_id.return_value = trace_id
        mock_generate_span_id.return_value = span_id

        def mock_set_value_impl(key, value, context=None):
            if context is None:
                context = {}
            context[fixed_key] = value
            return context

        mock_set_value.side_effect = mock_set_value_impl

        def mock_get_span_impl(context=None):
            if context is None or fixed_key not in context:
                return INVALID_SPAN
            return context[fixed_key]

        mock_get_current_span.side_effect = mock_get_span_impl

        _, _ = set_up_test_logging(logging.WARNING)
        tracer = trace.TracerProvider().get_tracer(__name__)

        with tracer.start_as_current_span("test") as span:
            context = set_span_in_context(span)
            span_context = span.get_span_context()

            expected = json.dumps(
                {
                    "body": "a log line",
                    "severity_number": None,
                    "severity_text": None,
                    "attributes": {
                        "mapping": {"key": "value"},
                        "none": None,
                        "sequence": [1, 2],
                        "str": "string",
                    },
                    "dropped_attributes": 0,
                    "timestamp": "1970-01-01T00:00:00.000000Z",
                    "observed_timestamp": "1970-01-01T00:00:00.000000Z",
                    "context": {
                        fixed_key: f'_Span(name="test", context=SpanContext(trace_id=0x{format_trace_id(trace_id)}, '
                        f"span_id=0x{format_span_id(span_id)}, "
                        f"trace_flags=0x01, trace_state=[], is_remote=False))"
                    },
                    "trace_id": f"0x{format_trace_id(span_context.trace_id)}",
                    "span_id": f"0x{format_span_id(span_context.span_id)}",
                    "trace_flags": span_context.trace_flags,
                    "resource": {
                        "attributes": {"service.name": "foo"},
                        "schema_url": "",
                    },
                },
                indent=4,
            )

            actual = LogRecord(
                timestamp=0,
                observed_timestamp=0,
                context=context,
                body="a log line",
                resource=Resource({"service.name": "foo"}),
                attributes={
                    "mapping": {"key": "value"},
                    "none": None,
                    "sequence": [1, 2],
                    "str": "string",
                },
            )

            self.assertEqual(expected, actual.to_json(indent=4))
            self.assertEqual(
                '{"body": "a log line", "severity_number": null, "severity_text": null, "attributes": {"mapping": {"key": "value"}, "none": null, "sequence": [1, 2], "str": "string"}, "dropped_attributes": 0, "timestamp": "1970-01-01T00:00:00.000000Z", "observed_timestamp": "1970-01-01T00:00:00.000000Z", "context": {"current-span-test": "_Span(name=\\"test\\", context=SpanContext(trace_id=0x000000000000000000000000deadbeef, span_id=0x00000000deadbef0, trace_flags=0x01, trace_state=[], is_remote=False))"}, "trace_id": "0x000000000000000000000000deadbeef", "span_id": "0x00000000deadbef0", "trace_flags": 1, "resource": {"attributes": {"service.name": "foo"}, "schema_url": ""}}',
                actual.to_json(indent=None),
            )

    def test_log_record_to_json_serializes_severity_number_as_int(self):
        actual = LogRecord(
            timestamp=0,
            severity_number=SeverityNumber.WARN,
            observed_timestamp=0,
            body="a log line",
            resource=Resource({"service.name": "foo"}),
        )

        decoded = json.loads(actual.to_json())
        self.assertEqual(SeverityNumber.WARN.value, decoded["severity_number"])

    def test_log_record_bounded_attributes(self):
        attr = {"key": "value"}

        result = LogRecord(timestamp=0, body="a log line", attributes=attr)

        self.assertTrue(isinstance(result.attributes, BoundedAttributes))

    def test_log_record_dropped_attributes_empty_limits(self):
        attr = {"key": "value"}

        result = LogRecord(timestamp=0, body="a log line", attributes=attr)

        self.assertTrue(result.dropped_attributes == 0)

    def test_log_record_dropped_attributes_set_limits_max_attribute(self):
        attr = {"key": "value", "key2": "value2"}
        limits = LogLimits(
            max_attributes=1,
        )

        result = LogRecord(
            timestamp=0, body="a log line", attributes=attr, limits=limits
        )
        self.assertTrue(result.dropped_attributes == 1)

    def test_log_record_dropped_attributes_set_limits_max_attribute_length(
        self,
    ):
        attr = {"key": "value", "key2": "value2"}
        expected = {"key": "v", "key2": "v"}
        limits = LogLimits(
            max_attribute_length=1,
        )

        result = LogRecord(
            timestamp=0, body="a log line", attributes=attr, limits=limits
        )
        self.assertTrue(result.dropped_attributes == 0)
        self.assertEqual(expected, result.attributes)

    def test_log_record_dropped_attributes_set_limits(self):
        attr = {"key": "value", "key2": "value2"}
        expected = {"key2": "v"}
        limits = LogLimits(
            max_attributes=1,
            max_attribute_length=1,
        )

        result = LogRecord(
            timestamp=0, body="a log line", attributes=attr, limits=limits
        )
        self.assertTrue(result.dropped_attributes == 1)
        self.assertEqual(expected, result.attributes)

    def test_log_record_dropped_attributes_set_limits_warning_once(self):
        attr = {"key1": "value1", "key2": "value2"}
        limits = LogLimits(
            max_attributes=1,
            max_attribute_length=1,
        )

        with warnings.catch_warnings(record=True) as cw:
            for _ in range(10):
                LogRecord(
                    timestamp=0,
                    body="a log line",
                    attributes=attr,
                    limits=limits,
                )
        self.assertEqual(len(cw), 1)
        self.assertIsInstance(cw[-1].message, LogDroppedAttributesWarning)
        self.assertIn(
            "Log record attributes were dropped due to limits",
            str(cw[-1].message),
        )

    def test_log_record_dropped_attributes_unset_limits(self):
        attr = {"key": "value", "key2": "value2"}
        limits = LogLimits()

        result = LogRecord(
            timestamp=0, body="a log line", attributes=attr, limits=limits
        )
        self.assertTrue(result.dropped_attributes == 0)
        self.assertEqual(attr, result.attributes)


def set_up_test_logging(level, formatter=None, root_logger=False):
    logger_provider = LoggerProvider()
    processor = FakeProcessor()
    logger_provider.add_log_record_processor(processor)
    logger = logging.getLogger(None if root_logger else "foo")
    handler = LoggingHandler(level=level, logger_provider=logger_provider)
    if formatter:
        handler.setFormatter(formatter)
    logger.addHandler(handler)
    return processor, logger


class FakeProcessor(LogRecordProcessor):
    def __init__(self):
        self.log_data_emitted = []

    def emit(self, log_data: LogData):
        self.log_data_emitted.append(log_data)

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis: int = 30000):
        pass

    def emit_count(self):
        return len(self.log_data_emitted)

    def get_log_record(self, i):
        return self.log_data_emitted[i].log_record
