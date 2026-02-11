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
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Generator

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
SRC_PATH = PROJECT_ROOT / "src"
PROTO_PATH = Path(__file__).parent / "proto"
GEN_PATH = Path(__file__).parent / "generated"

WRAPPER_CONTENT = f"""#!/usr/bin/env python3
import sys
sys.path.insert(0, "{SRC_PATH.absolute()}")
from opentelemetry.codegen.json.plugin import main
if __name__ == "__main__":
    main()
"""


@pytest.fixture(scope="module", autouse=True)
def generate_code() -> Generator[None, None, None]:
    if GEN_PATH.exists():
        shutil.rmtree(GEN_PATH)
    GEN_PATH.mkdir(parents=True)

    wrapper_path = PROJECT_ROOT / "protoc-gen-otlp_json_wrapper.py"
    wrapper_path.write_text(WRAPPER_CONTENT)
    wrapper_path.chmod(0o755)

    try:
        protos = list(PROTO_PATH.glob("**/*.proto"))
        proto_files = [str(p.relative_to(PROTO_PATH)) for p in protos]

        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "grpc_tools.protoc",
                f"-I{PROTO_PATH}",
                f"--plugin=protoc-gen-otlp_json={wrapper_path}",
                f"--otlp_json_out={GEN_PATH}",
                *proto_files,
            ]
        )

        sys.path.insert(0, str(GEN_PATH.absolute()))
        yield
    finally:
        if wrapper_path.exists():
            wrapper_path.unlink()


def test_generated_message_roundtrip() -> None:
    from otel_test_json.test.v1.test import SubMessage, TestMessage  # type: ignore

    msg = TestMessage(
        name="test",
        int_value=123,
        bool_value=True,
        double_value=1.5,
        int64_value=9223372036854775807,
        uint64_value=18446744073709551615,
        bytes_value=b"hello",
        trace_id=b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\x0d\x0e\x0f",
        span_id=b"\x00\x01\x02\x03\x04\x05\x06",
        list_strings=["a", "b"],
        list_ints=[1, 2],
        enum_value=TestMessage.TestEnum.SUCCESS,
        sub_message=SubMessage(content="sub"),
        list_messages=[SubMessage(content="m1"), SubMessage(content="m2")],
        oneof_string="oneof",
    )

    json_str = msg.to_json()
    data = json.loads(json_str)

    assert data["name"] == "test"
    assert data["intValue"] == 123
    assert data["boolValue"] is True
    assert data["doubleValue"] == 1.5
    assert data["int64Value"] == "9223372036854775807"
    assert data["uint64Value"] == "18446744073709551615"
    assert data["bytesValue"] == "aGVsbG8="
    assert data["traceId"] == "000102030405060708090a0b0c0d0e0f"
    assert data["spanId"] == "00010203040506"
    assert data["listStrings"] == ["a", "b"]
    assert data["listInts"] == [1, 2]
    assert data["enumValue"] == 1
    assert data["subMessage"]["content"] == "sub"
    assert len(data["listMessages"]) == 2
    assert data["oneofString"] == "oneof"
    assert "oneofInt" not in data

    new_msg = TestMessage.from_json(json_str)
    assert new_msg == msg


def test_cross_reference() -> None:
    from otel_test_json.common.v1.common import InstrumentationScope  # type: ignore
    from otel_test_json.trace.v1.trace import Span  # type: ignore

    span = Span(
        name="my-span",
        scope=InstrumentationScope(name="my-scope", version="1.0.0"),
    )

    json_str = span.to_json()
    data = json.loads(json_str)

    assert data["name"] == "my-span"
    assert data["scope"]["name"] == "my-scope"
    assert data["scope"]["version"] == "1.0.0"

    new_span = Span.from_json(json_str)
    assert new_span == span


@pytest.mark.parametrize(
    "field, value, expected_json_val",
    [
        ("d_val", float("nan"), "NaN"),
        ("d_val", float("inf"), "Infinity"),
        ("d_val", float("-inf"), "-Infinity"),
        ("d_val", 0.0, None),  # Default values are omitted
        ("d_val", -0.0, None),
        ("i64_val", 9223372036854775807, "9223372036854775807"),
        ("i64_val", -9223372036854775808, "-9223372036854775808"),
        ("u64_val", 18446744073709551615, "18446744073709551615"),
        ("i32_val", 2147483647, 2147483647),
        ("i32_val", -2147483648, -2147483648),
        ("u32_val", 4294967295, 4294967295),
        ("si32_val", -123, -123),
        ("si64_val", -456, "-456"),
        ("f32_val", 789, 789),
        ("f64_val", 101112, "101112"),
        ("sf32_val", -131415, -131415),
        ("sf64_val", -161718, "-161718"),
    ],
)
def test_numeric_types(field: str, value: Any, expected_json_val: Any) -> None:
    from otel_test_json.test.v1.complex import NumericTest  # type: ignore

    msg = NumericTest(**{field: value})
    data = msg.to_dict()

    # Convert snake_case to lowerCamelCase for lookup
    components = field.split("_")
    json_field = components[0] + "".join(x.title() for x in components[1:])

    if expected_json_val is None:
        assert json_field not in data
    else:
        assert data[json_field] == expected_json_val

    new_msg = NumericTest.from_dict(data)
    if isinstance(value, float) and math.isnan(value):
        assert math.isnan(getattr(new_msg, field))
    else:
        assert getattr(new_msg, field) == value


@pytest.mark.parametrize(
    "kwargs, expected_data",
    [
        ({"g1_string": "hello"}, {"g1String": "hello"}),
        ({"g1_int": 42}, {"g1Int": 42}),
        ({"g2_message": {"name": "scope"}}, {"g2Message": {"name": "scope"}}),
        ({"g2_nested": {"hint": "test"}}, {"g2Nested": {"hint": "test"}}),
    ],
)
def test_oneof_suite_variants(
    kwargs: dict[str, Any], expected_data: dict[str, Any]
) -> None:
    from otel_test_json.common.v1.common import InstrumentationScope  # type: ignore
    from otel_test_json.test.v1.complex import OneofSuite  # type: ignore

    processed_kwargs = {}
    for k, v in kwargs.items():
        if k == "g2_message":
            processed_kwargs[k] = InstrumentationScope(**v)
        elif k == "g2_nested":
            processed_kwargs[k] = OneofSuite.NestedMessage(**v)
        else:
            processed_kwargs[k] = v

    msg = OneofSuite(**processed_kwargs)
    data = msg.to_dict()
    assert data == expected_data

    new_msg = OneofSuite.from_dict(data)
    for k, v in processed_kwargs.items():
        assert getattr(new_msg, k) == v


@pytest.mark.parametrize(
    "kwargs, expected_dict",
    [
        ({}, {}),
        ({"opt_string": ""}, {}),
        ({"opt_string": "foo"}, {"optString": "foo"}),
        ({"opt_int": 0}, {}),
        ({"opt_int": 42}, {"optInt": 42}),
        ({"opt_bool": False}, {}),
        ({"opt_bool": True}, {"optBool": True}),
    ],
)
def test_optional_scalars(
    kwargs: dict[str, Any], expected_dict: dict[str, Any]
) -> None:
    from otel_test_json.test.v1.complex import OptionalScalar  # type: ignore

    msg = OptionalScalar(**kwargs)
    assert msg.to_dict() == expected_dict
    assert OptionalScalar.from_dict(expected_dict) == msg


def test_nested_enum_suite() -> None:
    from otel_test_json.test.v1.complex import NestedEnumSuite  # type: ignore

    msg = NestedEnumSuite(
        nested=NestedEnumSuite.NestedEnum.NESTED_FOO,
        repeated_nested=[
            NestedEnumSuite.NestedEnum.NESTED_FOO,
            NestedEnumSuite.NestedEnum.NESTED_BAR,
        ],
    )

    data = msg.to_dict()
    assert data["nested"] == 1
    assert data["repeatedNested"] == [1, 2]

    new_msg = NestedEnumSuite.from_dict(data)
    assert new_msg.nested == NestedEnumSuite.NestedEnum.NESTED_FOO
    assert new_msg.repeated_nested == msg.repeated_nested


def test_deeply_nested() -> None:
    from otel_test_json.test.v1.complex import DeeplyNested  # type: ignore

    msg = DeeplyNested(
        value="1",
        next=DeeplyNested(value="2", next=DeeplyNested(value="3")),
    )

    data = msg.to_dict()
    assert data["value"] == "1"
    assert data["next"]["value"] == "2"
    assert data["next"]["next"]["value"] == "3"

    new_msg = DeeplyNested.from_dict(data)
    assert new_msg.value == "1"
    assert new_msg.next.value == "2"
    assert new_msg.next.next.value == "3"


@pytest.mark.parametrize(
    "data, expected_name, expected_int",
    [
        ({"name": None, "intValue": None}, "", 0),
        ({"name": "test"}, "test", 0),
        ({"intValue": 42}, "", 42),
    ],
)
def test_defaults_and_none(
    data: dict[str, Any], expected_name: str, expected_int: int
) -> None:
    from otel_test_json.test.v1.test import TestMessage  # type: ignore

    msg = TestMessage.from_dict(data)
    assert msg.name == expected_name
    assert msg.int_value == expected_int


@pytest.mark.parametrize(
    "data, expected_error, match",
    [
        ({"intValue": "not an int"}, TypeError, "expected <class 'int'>"),
        ({"traceId": "invalid hex"}, ValueError, "Invalid hex string"),
        ({"listStrings": "not a list"}, TypeError, "expected <class 'list'>"),
        ({"name": 123}, TypeError, "expected <class 'str'>"),
        ({"subMessage": "not a dict"}, TypeError, "expected <class 'dict'>"),
        ({"enumValue": "SUCCESS"}, TypeError, "expected <class 'int'>"),
        ({"listMessages": [None]}, TypeError, "expected <class 'dict'>"),
    ],
)
def test_validation_errors(
    data: dict[str, Any], expected_error: type, match: str
) -> None:
    from otel_test_json.test.v1.test import TestMessage  # type: ignore

    with pytest.raises(
        expected_error, match=match if expected_error == TypeError else None
    ):
        TestMessage.from_dict(data)


def test_unknown_fields_ignored() -> None:
    from otel_test_json.test.v1.test import TestMessage  # type: ignore

    # Unknown fields should be ignored for forward compatibility
    data = {
        "name": "test",
        "unknownField": "should be ignored",
        "intValue": 10,
    }
    msg = TestMessage.from_dict(data)
    assert msg.name == "test"
    assert msg.int_value == 10
