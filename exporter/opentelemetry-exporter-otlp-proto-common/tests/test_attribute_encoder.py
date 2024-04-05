import unittest
from unittest.mock import patch

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
            ],
        )

    @patch(
        "opentelemetry.exporter.otlp.proto.common._internal._logger.exception"
    )
    def test_encode_attributes_error_logs_key(self, mock_logger_exception):
        result = _encode_attributes({"a": 1, "bad_key": None, "b": 2})
        mock_logger_exception.assert_called_once()
        self.assertEqual(
            mock_logger_exception.call_args_list[0].args[0],
            "Failed to encode key %s: %s",
        )
        self.assertEqual(
            mock_logger_exception.call_args_list[0].args[1], "bad_key"
        )
        self.assertTrue(
            isinstance(
                mock_logger_exception.call_args_list[0].args[2], Exception
            )
        )
        self.assertEqual(
            result,
            [
                PB2KeyValue(key="a", value=PB2AnyValue(int_value=1)),
                PB2KeyValue(key="b", value=PB2AnyValue(int_value=2)),
            ],
        )
