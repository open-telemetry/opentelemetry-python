import pytest
from google.protobuf import descriptor_pb2 as descriptor

from opentelemetry.codegen.json.types import (
    PROTO_DEFAULTS,
    PROTO_TO_PYTHON,
    get_default_value,
    get_python_type,
)

FDP = descriptor.FieldDescriptorProto


@pytest.mark.parametrize(
    "proto_type, expected",
    [
        (FDP.TYPE_DOUBLE, "0.0"),
        (FDP.TYPE_FLOAT, "0.0"),
        (FDP.TYPE_INT64, "0"),
        (FDP.TYPE_UINT32, "0"),
        (FDP.TYPE_SINT64, "0"),
        (FDP.TYPE_BOOL, "False"),
        (FDP.TYPE_STRING, '""'),
        (FDP.TYPE_BYTES, 'b""'),
    ],
)
def test_get_default_value_known_types(proto_type, expected):
    assert get_default_value(proto_type) == expected


@pytest.mark.parametrize(
    "proto_type",
    [FDP.TYPE_GROUP, FDP.TYPE_MESSAGE, FDP.TYPE_ENUM],
)
def test_get_default_value_valid_types_without_default(proto_type):
    assert get_default_value(proto_type) == "None"


@pytest.mark.parametrize("proto_type", [0, -1, 999, 2**31])
def test_get_default_value_out_of_range(proto_type):
    assert get_default_value(proto_type) == "None"


def test_every_mapped_type_has_a_default():
    # keeps PROTO_TO_PYTHON and PROTO_DEFAULTS from drifting apart
    assert set(PROTO_TO_PYTHON) == set(PROTO_DEFAULTS)


@pytest.mark.parametrize("proto_type", PROTO_DEFAULTS)
def test_default_is_valid_python_literal(proto_type):
    # the default is emitted into generated code, so it must eval cleanly
    value = eval(get_default_value(proto_type))
    expected_type = eval(get_python_type(proto_type).replace("builtins.", ""))
    assert isinstance(value, expected_type)