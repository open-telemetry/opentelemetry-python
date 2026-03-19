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

# pylint: disable=protected-access

import base64
import unittest
from logging import ERROR

from opentelemetry.exporter.otlp.json.common._internal import (
    _encode_array,
    _encode_attributes,
    _encode_instrumentation_scope,
    _encode_key_value,
    _encode_resource,
    _encode_span_id,
    _encode_trace_id,
    _encode_value,
)
from opentelemetry.proto_json.common.v1.common import AnyValue as JSONAnyValue
from opentelemetry.proto_json.common.v1.common import (
    ArrayValue as JSONArrayValue,
)
from opentelemetry.proto_json.common.v1.common import (
    InstrumentationScope as JSONInstrumentationScope,
)
from opentelemetry.proto_json.common.v1.common import KeyValue as JSONKeyValue
from opentelemetry.proto_json.common.v1.common import (
    KeyValueList as JSONKeyValueList,
)
from opentelemetry.proto_json.resource.v1.resource import (
    Resource as JSONResource,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope


class TestCommonEncoder(unittest.TestCase):
    def test_encode_value(self):
        cases = [
            (
                "string",
                "hello",
                JSONAnyValue(string_value="hello"),
                {"stringValue": "hello"},
            ),
            (
                "bool_true",
                True,
                JSONAnyValue(bool_value=True),
                {"boolValue": True},
            ),
            (
                "bool_false",
                False,
                JSONAnyValue(bool_value=False),
                {"boolValue": False},
            ),
            (
                "int",
                42,
                JSONAnyValue(int_value=42),
                {"intValue": "42"},
            ),
            (
                "int_zero",
                0,
                JSONAnyValue(int_value=0),
                {"intValue": "0"},
            ),
            (
                "int_negative",
                -7,
                JSONAnyValue(int_value=-7),
                {"intValue": "-7"},
            ),
            (
                "float",
                3.14,
                JSONAnyValue(double_value=3.14),
                {"doubleValue": 3.14},
            ),
            (
                "bytes",
                b"\x01\x02\x03",
                JSONAnyValue(bytes_value=b"\x01\x02\x03"),
                {
                    "bytesValue": base64.b64encode(b"\x01\x02\x03").decode(
                        "utf-8"
                    )
                },
            ),
        ]
        for name, value, expected_obj, expected_dict in cases:
            with self.subTest(name=name):
                result = _encode_value(value)
                self.assertEqual(result, expected_obj)
                self.assertEqual(result.to_dict(), expected_dict)

    def test_encode_value_sequence(self):
        result = _encode_value([1, 2, 3])
        expected = JSONAnyValue(
            array_value=JSONArrayValue(
                values=[
                    JSONAnyValue(int_value=1),
                    JSONAnyValue(int_value=2),
                    JSONAnyValue(int_value=3),
                ]
            )
        )
        self.assertEqual(result, expected)
        result_dict = result.to_dict()
        self.assertIn("arrayValue", result_dict)
        self.assertEqual(len(result_dict["arrayValue"]["values"]), 3)

    def test_encode_value_mapping(self):
        result = _encode_value({"key": "val", "num": 1})
        expected = JSONAnyValue(
            kvlist_value=JSONKeyValueList(
                values=[
                    JSONKeyValue(
                        key="key", value=JSONAnyValue(string_value="val")
                    ),
                    JSONKeyValue(key="num", value=JSONAnyValue(int_value=1)),
                ]
            )
        )
        self.assertEqual(result, expected)
        result_dict = result.to_dict()
        self.assertIn("kvlistValue", result_dict)

    def test_encode_value_none_not_allowed(self):
        with self.assertRaises(TypeError):
            _encode_value(None)

    def test_encode_value_none_allowed(self):
        result = _encode_value(None, allow_null=True)
        self.assertIsNone(result)

    def test_encode_array_with_nulls(self):
        result = _encode_array([1, None, 2], allow_null=True)
        self.assertEqual(
            result,
            [
                JSONAnyValue(int_value=1),
                JSONAnyValue(),
                JSONAnyValue(int_value=2),
            ],
        )
        self.assertEqual(result[1].to_dict(), {})

    def test_encode_array_none_raises(self):
        with self.assertRaises(TypeError):
            _encode_array([1, None, 2], allow_null=False)

    def test_encode_key_value(self):
        result = _encode_key_value("mykey", "myval")
        expected = JSONKeyValue(
            key="mykey", value=JSONAnyValue(string_value="myval")
        )
        self.assertEqual(result, expected)
        self.assertEqual(
            result.to_dict(),
            {"key": "mykey", "value": {"stringValue": "myval"}},
        )

    def test_encode_attributes_all_types(self):
        result = _encode_attributes(
            {
                "a": 1,
                "b": 3.14,
                "c": False,
                "hello": "world",
                "greet": ["hola", "bonjour"],
                "data": [1, 2],
                "data_granular": [1.4, 2.4],
                "binary_data": b"x00\x01\x02",
            }
        )
        self.assertEqual(
            result,
            [
                JSONKeyValue(key="a", value=JSONAnyValue(int_value=1)),
                JSONKeyValue(key="b", value=JSONAnyValue(double_value=3.14)),
                JSONKeyValue(key="c", value=JSONAnyValue(bool_value=False)),
                JSONKeyValue(
                    key="hello", value=JSONAnyValue(string_value="world")
                ),
                JSONKeyValue(
                    key="greet",
                    value=JSONAnyValue(
                        array_value=JSONArrayValue(
                            values=[
                                JSONAnyValue(string_value="hola"),
                                JSONAnyValue(string_value="bonjour"),
                            ]
                        )
                    ),
                ),
                JSONKeyValue(
                    key="data",
                    value=JSONAnyValue(
                        array_value=JSONArrayValue(
                            values=[
                                JSONAnyValue(int_value=1),
                                JSONAnyValue(int_value=2),
                            ]
                        )
                    ),
                ),
                JSONKeyValue(
                    key="data_granular",
                    value=JSONAnyValue(
                        array_value=JSONArrayValue(
                            values=[
                                JSONAnyValue(double_value=1.4),
                                JSONAnyValue(double_value=2.4),
                            ]
                        )
                    ),
                ),
                JSONKeyValue(
                    key="binary_data",
                    value=JSONAnyValue(bytes_value=b"x00\x01\x02"),
                ),
            ],
        )

    def test_encode_attributes_empty(self):
        self.assertIsNone(_encode_attributes({}))
        self.assertIsNone(_encode_attributes(None))

    def test_encode_attributes_error_skips_bad_key(self):
        with self.assertLogs(level=ERROR) as error:
            result = _encode_attributes({"a": 1, "bad_key": None, "b": 2})

        self.assertEqual(len(error.records), 1)
        self.assertEqual(error.records[0].msg, "Failed to encode key %s: %s")
        self.assertEqual(error.records[0].args[0], "bad_key")
        self.assertIsInstance(error.records[0].args[1], Exception)
        self.assertEqual(
            result,
            [
                JSONKeyValue(key="a", value=JSONAnyValue(int_value=1)),
                JSONKeyValue(key="b", value=JSONAnyValue(int_value=2)),
            ],
        )

    def test_encode_attributes_error_list_none(self):
        with self.assertLogs(level=ERROR) as error:
            result = _encode_attributes(
                {"a": 1, "bad_key": ["test", None, "test"], "b": 2}
            )

        self.assertEqual(len(error.records), 1)
        self.assertEqual(error.records[0].msg, "Failed to encode key %s: %s")
        self.assertEqual(error.records[0].args[0], "bad_key")
        self.assertIsInstance(error.records[0].args[1], Exception)
        self.assertEqual(
            result,
            [
                JSONKeyValue(key="a", value=JSONAnyValue(int_value=1)),
                JSONKeyValue(key="b", value=JSONAnyValue(int_value=2)),
            ],
        )

    def test_encode_span_id(self):
        span_id = 0x1234567890ABCDEF
        result = _encode_span_id(span_id)
        self.assertEqual(result, b"\x12\x34\x56\x78\x90\xab\xcd\xef")
        self.assertEqual(len(result), 8)

    def test_encode_trace_id(self):
        trace_id = 0x3E0C63257DE34C926F9EFCD03927272E
        result = _encode_trace_id(trace_id)
        self.assertEqual(
            result,
            b"\x3e\x0c\x63\x25\x7d\xe3\x4c\x92\x6f\x9e\xfc\xd0\x39\x27\x27\x2e",
        )
        self.assertEqual(len(result), 16)

    def test_encode_resource(self):
        resource = Resource({"key": "val"})
        result = _encode_resource(resource)
        expected = JSONResource(
            attributes=[
                JSONKeyValue(key="key", value=JSONAnyValue(string_value="val"))
            ]
        )
        self.assertEqual(result, expected)
        result_dict = result.to_dict()
        self.assertIn("attributes", result_dict)
        self.assertEqual(len(result_dict["attributes"]), 1)
        self.assertEqual(
            result_dict["attributes"][0],
            {"key": "key", "value": {"stringValue": "val"}},
        )

    def test_encode_resource_empty(self):
        resource = Resource({})
        result = _encode_resource(resource)
        self.assertEqual(result, JSONResource(attributes=None))
        self.assertEqual(result.to_dict(), {})

    def test_encode_instrumentation_scope(self):
        scope = InstrumentationScope(
            name="my_lib",
            version="1.0.0",
            attributes={"k": 1},
        )
        result = _encode_instrumentation_scope(scope)
        expected = JSONInstrumentationScope(
            name="my_lib",
            version="1.0.0",
            attributes=[
                JSONKeyValue(key="k", value=JSONAnyValue(int_value=1))
            ],
        )
        self.assertEqual(result, expected)
        result_dict = result.to_dict()
        self.assertEqual(result_dict["name"], "my_lib")
        self.assertEqual(result_dict["version"], "1.0.0")
        self.assertIn("attributes", result_dict)

    def test_encode_instrumentation_scope_none(self):
        result = _encode_instrumentation_scope(None)
        self.assertEqual(result, JSONInstrumentationScope())
        self.assertEqual(result.to_dict(), {})
