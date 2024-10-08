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

import unittest
from logging import ERROR

from opentelemetry.exporter.otlp.proto.common._internal import (
    _encode_attributes,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue as PB2AnyValue
from opentelemetry.proto.common.v1.common_pb2 import (
    ArrayValue as PB2ArrayValue,
)
from opentelemetry.proto.common.v1.common_pb2 import KeyValue as PB2KeyValue


class TestOTLPAttributeEncoder(unittest.TestCase):
    def test_encode_attributes_all_kinds(self):
        result = _encode_attributes(
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
        self.assertEqual(
            result,
            [
                PB2KeyValue(key="a", value=PB2AnyValue(int_value=1)),
                PB2KeyValue(key="b", value=PB2AnyValue(double_value=3.14)),
                PB2KeyValue(key="c", value=PB2AnyValue(bool_value=False)),
                PB2KeyValue(
                    key="hello", value=PB2AnyValue(string_value="world")
                ),
                PB2KeyValue(
                    key="greet",
                    value=PB2AnyValue(
                        array_value=PB2ArrayValue(
                            values=[
                                PB2AnyValue(string_value="hola"),
                                PB2AnyValue(string_value="bonjour"),
                            ]
                        )
                    ),
                ),
                PB2KeyValue(
                    key="data",
                    value=PB2AnyValue(
                        array_value=PB2ArrayValue(
                            values=[
                                PB2AnyValue(int_value=1),
                                PB2AnyValue(int_value=2),
                            ]
                        )
                    ),
                ),
                PB2KeyValue(
                    key="data_granular",
                    value=PB2AnyValue(
                        array_value=PB2ArrayValue(
                            values=[
                                PB2AnyValue(double_value=1.4),
                                PB2AnyValue(double_value=2.4),
                            ]
                        )
                    ),
                ),
                PB2KeyValue(
                    key="binary_data",
                    value=PB2AnyValue(bytes_value=b"x00\x01\x02"),
                ),
            ],
        )

    def test_encode_attributes_error_logs_key(self):
        with self.assertLogs(level=ERROR) as error:
            result = _encode_attributes({"a": 1, "bad_key": None, "b": 2})

        self.assertEqual(len(error.records), 1)
        self.assertEqual(error.records[0].msg, "Failed to encode key %s: %s")
        self.assertEqual(error.records[0].args[0], "bad_key")
        self.assertIsInstance(error.records[0].args[1], Exception)
        self.assertEqual(
            result,
            [
                PB2KeyValue(key="a", value=PB2AnyValue(int_value=1)),
                PB2KeyValue(key="b", value=PB2AnyValue(int_value=2)),
            ],
        )
