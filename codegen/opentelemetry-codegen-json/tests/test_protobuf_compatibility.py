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

# ruff: noqa: PLC0415

import base64
from typing import Any, Type

import pytest
from google.protobuf import json_format


def normalize_otlp_json(data: Any) -> Any:
    if isinstance(data, list):
        return [normalize_otlp_json(item) for item in data]
    if isinstance(data, dict):
        return {
            key: (
                base64.b64decode(value).hex()
                if key in {"traceId", "spanId", "parentSpanId"}
                and isinstance(value, str)
                else normalize_otlp_json(value)
            )
            for key, value in data.items()
        }
    return data


@pytest.fixture
def test_msg_classes() -> tuple[Type[Any], Type[Any], Type[Any]]:
    from otel_test_json.test.v1.test import SubMessage as JSONSubMessage
    from otel_test_json.test.v1.test import TestMessage as JSONTestMessage
    from otel_test_json.test.v1.test_pb2 import TestMessage as ProtoTestMessage

    return JSONTestMessage, JSONSubMessage, ProtoTestMessage


@pytest.fixture
def numeric_msg_classes() -> tuple[Type[Any], Type[Any]]:
    from otel_test_json.test.v1.complex import NumericTest as JSONNumericTest
    from otel_test_json.test.v1.complex_pb2 import (
        NumericTest as ProtoNumericTest,
    )

    return JSONNumericTest, ProtoNumericTest


@pytest.fixture
def oneof_msg_classes() -> tuple[Type[Any], Type[Any], Type[Any]]:
    from otel_test_json.common.v1.common import (
        InstrumentationScope as JSONScope,
    )
    from otel_test_json.test.v1.complex import OneofSuite as JSONOneofSuite
    from otel_test_json.test.v1.complex_pb2 import (
        OneofSuite as ProtoOneofSuite,
    )

    return JSONOneofSuite, ProtoOneofSuite, JSONScope


@pytest.fixture
def optional_msg_classes() -> tuple[Type[Any], Type[Any]]:
    from otel_test_json.test.v1.complex import (
        OptionalScalar as JSONOptionalScalar,
    )
    from otel_test_json.test.v1.complex_pb2 import (
        OptionalScalar as ProtoOptionalScalar,
    )

    return JSONOptionalScalar, ProtoOptionalScalar


def test_parity_test_message(
    test_msg_classes: tuple[Type[Any], Type[Any], Type[Any]],
) -> None:
    JSONTestMessage, JSONSubMessage, ProtoTestMessage = test_msg_classes

    kwargs: dict[str, Any] = {
        "name": "test",
        "int_value": 123,
        "bool_value": True,
        "double_value": 1.5,
        "int64_value": 9223372036854775807,
        "uint64_value": 18446744073709551615,
        "bytes_value": b"hello",
        "trace_id": b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\x0d\x0e\x0f",
        "span_id": b"\x00\x01\x02\x03\x04\x05\x06\x07",
        "list_strings": ["a", "b"],
        "list_ints": [1, 2],
        "enum_value": JSONTestMessage.TestEnum.SUCCESS,
        "oneof_string": "oneof",
        "sub_message": JSONSubMessage(content="sub"),
    }

    json_msg = JSONTestMessage(**kwargs)
    json_dict = json_msg.to_dict()

    proto_kwargs = kwargs.copy()
    sub_msg_data = proto_kwargs.pop("sub_message")
    proto_msg = ProtoTestMessage(**proto_kwargs)
    proto_msg.sub_message.content = sub_msg_data.content

    proto_dict = json_format.MessageToDict(
        proto_msg,
        preserving_proto_field_name=False,
        use_integers_for_enums=True,
    )

    assert json_dict == normalize_otlp_json(proto_dict)


@pytest.mark.parametrize(
    "values",
    [
        {"d_val": float("nan")},
        {"f_val": float("inf")},
        {"f_val": float("-inf")},
        {"i64_val": 9223372036854775807},
        {"i64_val": -9223372036854775808},
        {"u64_val": 18446744073709551615},
        {"i32_val": -2147483648},
        {"i32_val": 2147483647},
        {"si64_val": -9223372036854775808},
        {"f64_val": 9223372036854775807},
    ],
)
def test_parity_numeric_test(
    numeric_msg_classes: tuple[Type[Any], Type[Any]], values: dict[str, Any]
) -> None:
    JSONNumericTest, ProtoNumericTest = numeric_msg_classes

    json_msg = JSONNumericTest(**values)
    proto_msg = ProtoNumericTest(**values)

    json_dict = json_msg.to_dict()
    proto_dict = json_format.MessageToDict(
        proto_msg,
        use_integers_for_enums=True,
    )

    assert json_dict == normalize_otlp_json(proto_dict)


@pytest.mark.parametrize(
    "branch_data",
    [
        {"g1_string": "hello", "g2_nested": {"hint": "test"}},
        {"g1_int": 42, "g2_message": {"name": "scope"}},
    ],
)
def test_parity_oneof_suite(
    oneof_msg_classes: tuple[Type[Any], Type[Any], Type[Any]],
    branch_data: dict[str, Any],
) -> None:
    JSONOneofSuite, ProtoOneofSuite, JSONScope = oneof_msg_classes

    json_kwargs = {}
    for k, v in branch_data.items():
        if k == "g2_nested":
            json_kwargs[k] = JSONOneofSuite.NestedMessage(**v)
        elif k == "g2_message":
            json_kwargs[k] = JSONScope(**v)
        else:
            json_kwargs[k] = v

    json_msg = JSONOneofSuite(**json_kwargs)

    proto_msg = ProtoOneofSuite()
    for k, v in branch_data.items():
        if k == "g1_string":
            proto_msg.g1_string = v
        elif k == "g1_int":
            proto_msg.g1_int = v
        elif k == "g2_nested":
            proto_msg.g2_nested.hint = v["hint"]
        elif k == "g2_message":
            proto_msg.g2_message.name = v["name"]

    assert json_msg.to_dict() == normalize_otlp_json(
        json_format.MessageToDict(
            proto_msg,
            use_integers_for_enums=True,
        )
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"opt_string": "foo", "opt_int": 42, "opt_bool": True},
        {},
        {"opt_string": "", "opt_int": 0, "opt_bool": False},
    ],
)
def test_parity_optional_scalars(
    optional_msg_classes: tuple[Type[Any], Type[Any]], kwargs: dict[str, Any]
) -> None:
    JSONOptionalScalar, ProtoOptionalScalar = optional_msg_classes

    json_msg = JSONOptionalScalar(**kwargs)
    proto_msg = ProtoOptionalScalar(**kwargs)

    assert json_msg.to_dict() == normalize_otlp_json(
        json_format.MessageToDict(
            proto_msg,
            use_integers_for_enums=True,
        )
    )
