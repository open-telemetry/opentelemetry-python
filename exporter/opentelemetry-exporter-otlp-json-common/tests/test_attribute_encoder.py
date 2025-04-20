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

# pylint: disable=unsubscriptable-object
import unittest
from logging import ERROR
from typing import Any, Dict, Optional

from opentelemetry.exporter.otlp.json.common._internal import (
    _encode_array,
    _encode_attributes,
    _encode_key_value,
    _encode_span_id,
    _encode_trace_id,
    _encode_value,
)


class TestAttributeEncoder(unittest.TestCase):
    def test_encode_attributes_all_kinds(self):
        # Test encoding all kinds of attributes
        result: Optional[Dict[str, Any]] = _encode_attributes(
            {
                "a": 1,  # int
                "b": 3.14,  # float
                "c": False,  # bool
                "hello": "world",  # str
                "greet": ["hola", "bonjour"],  # Sequence[str]
                "data": [1, 2],  # Sequence[int]
                "data_granular": [1.4, 2.4],  # Sequence[float]
                "binary_data": b"x00\x01\x02",  # bytes
            }
        )

        # Verify each key and value type
        self.assertIsNotNone(result, "Result should not be None")
        # Now we can safely use result as a dictionary since we've verified it's not None
        assert (
            result is not None
        )  # This helps type checkers understand result is not None
        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b"], 3.14)
        self.assertEqual(result["c"], False)
        self.assertEqual(result["hello"], "world")
        self.assertEqual(result["greet"], ["hola", "bonjour"])
        self.assertEqual(result["data"], [1, 2])
        self.assertEqual(result["data_granular"], [1.4, 2.4])
        self.assertIn("bytes_value", result["binary_data"])  # Base64 encoded

    def test_encode_attributes_error_list_none(self):
        # Test handling of None in a list
        with self.assertLogs(level=ERROR) as error:
            result: Optional[Dict[str, Any]] = _encode_attributes(
                {"a": 1, "bad_key": ["test", None, "test"], "b": 2}
            )

        # Verify error is logged
        self.assertEqual(len(error.records), 1)
        self.assertEqual(error.records[0].msg, "Failed to encode key %s: %s")
        self.assertEqual(error.records[0].args[0], "bad_key")
        self.assertIsInstance(error.records[0].args[1], Exception)

        # Verify other keys are still processed
        self.assertIsNotNone(result, "Result should not be None")
        # Now we can safely use result as a dictionary since we've verified it's not None
        assert (
            result is not None
        )  # This helps type checkers understand result is not None
        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b"], 2)
        self.assertNotIn("bad_key", result)

    def test_encode_attributes_error_logs_key(self):
        # Test handling of None as a value
        with self.assertLogs(level=ERROR) as error:
            result: Optional[Dict[str, Any]] = _encode_attributes(
                {"a": 1, "bad_key": None, "b": 2}
            )

        # Verify error is logged
        self.assertEqual(len(error.records), 1)
        self.assertEqual(error.records[0].msg, "Failed to encode key %s: %s")
        self.assertEqual(error.records[0].args[0], "bad_key")
        self.assertIsInstance(error.records[0].args[1], Exception)

        # Verify other keys are still processed
        self.assertIsNotNone(result, "Result should not be None")
        # Now we can safely use result as a dictionary since we've verified it's not None
        assert (
            result is not None
        )  # This helps type checkers understand result is not None
        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b"], 2)
        self.assertNotIn("bad_key", result)

    def test_encode_value(self):
        # Test simple value encoding
        self.assertEqual(_encode_value(123), 123)
        self.assertEqual(_encode_value("test"), "test")
        self.assertEqual(_encode_value(True), True)
        self.assertEqual(_encode_value(3.14), 3.14)

        # Test array value encoding
        self.assertEqual(_encode_value([1, 2, 3]), [1, 2, 3])

        # Test mapping value encoding
        result: Dict[str, Any] = _encode_value({"a": 1, "b": 2})
        self.assertIsNotNone(result, "Result should not be None")
        # Now we can safely use result as a dictionary since we've verified it's not None
        assert (
            result is not None
        )  # This helps type checkers understand result is not None
        self.assertIn("kvlist_value", result)
        self.assertEqual(result["kvlist_value"]["a"], 1)
        self.assertEqual(result["kvlist_value"]["b"], 2)

        # Test bytes value encoding
        result_bytes: Dict[str, Any] = _encode_value(b"hello")
        self.assertIsNotNone(result_bytes, "Result_bytes should not be None")
        # Now we can safely use result_bytes as a dictionary since we've verified it's not None
        assert (
            result_bytes is not None
        )  # This helps type checkers understand result_bytes is not None
        self.assertIn("bytes_value", result_bytes)

        # Test None with allow_null=True
        self.assertIsNone(_encode_value(None, allow_null=True))

        # Test None with allow_null=False (should raise an exception)
        with self.assertRaises(Exception):
            _encode_value(None, allow_null=False)

        # Test unsupported type (should raise an exception)
        with self.assertRaises(Exception):
            _encode_value(complex(1, 2))

    def test_encode_array(self):
        # Test simple array encoding
        self.assertEqual(_encode_array([1, 2, 3]), [1, 2, 3])
        self.assertEqual(_encode_array(["a", "b"]), ["a", "b"])

        # Test array with None values and allow_null=True
        result = _encode_array([1, None, 2], allow_null=True)
        self.assertEqual(result, [1, None, 2])

        # Test array with None values and allow_null=False (should raise an exception)
        with self.assertRaises(Exception):
            _encode_array([1, None, 2], allow_null=False)

    def test_encode_key_value(self):
        # Test key-value encoding
        result = _encode_key_value("key", "value")
        self.assertEqual(result, {"key": "value"})

        result = _encode_key_value("num", 123)
        self.assertEqual(result, {"num": 123})

        # Test with None value and allow_null=True
        result = _encode_key_value("null_key", None, allow_null=True)
        self.assertEqual(result, {"null_key": None})

        # Test with None value and allow_null=False (should raise an exception)
        with self.assertRaises(Exception):
            _encode_key_value("null_key", None, allow_null=False)

    def test_encode_trace_id(self):
        # Test trace ID encoding
        trace_id = 0x3E0C63257DE34C926F9EFCD03927272E
        encoded = _encode_trace_id(trace_id)
        self.assertEqual(encoded, "3e0c63257de34c926f9efcd03927272e")
        self.assertEqual(len(encoded), 32)  # Should be 32 hex characters

    def test_encode_span_id(self):
        # Test span ID encoding
        span_id = 0x6E0C63257DE34C92
        encoded = _encode_span_id(span_id)
        self.assertEqual(encoded, "6e0c63257de34c92")
        self.assertEqual(len(encoded), 16)  # Should be 16 hex characters
