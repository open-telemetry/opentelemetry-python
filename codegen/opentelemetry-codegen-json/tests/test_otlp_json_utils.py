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

import math
from typing import Optional, Union

import pytest

from opentelemetry.codegen.json.runtime.otlp_json_utils import (
    decode_base64,
    decode_float,
    decode_hex,
    decode_int64,
    decode_repeated,
    encode_base64,
    encode_float,
    encode_hex,
    encode_int64,
    encode_repeated,
    validate_type,
)


@pytest.mark.parametrize(
    "value, expected",
    [
        (b"\x01\x02\x03", "010203"),
        (b"", ""),
        (None, ""),
    ],
)
def test_encode_hex(value: Optional[bytes], expected: str) -> None:
    assert encode_hex(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("010203", b"\x01\x02\x03"),
        ("", b""),
        (None, b""),
    ],
)
def test_decode_hex(value: Optional[str], expected: bytes) -> None:
    assert decode_hex(value, "field") == expected


def test_decode_hex_errors() -> None:
    with pytest.raises(TypeError):
        decode_hex(123, "field")  # type: ignore
    with pytest.raises(ValueError, match="Invalid hex string"):
        decode_hex("not hex", "field")


@pytest.mark.parametrize(
    "value, expected",
    [
        (b"hello", "aGVsbG8="),
        (b"", ""),
        (None, ""),
    ],
)
def test_encode_base64(value: Optional[bytes], expected: str) -> None:
    assert encode_base64(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("aGVsbG8=", b"hello"),
        ("", b""),
        (None, b""),
    ],
)
def test_decode_base64(value: Optional[str], expected: bytes) -> None:
    assert decode_base64(value, "field") == expected


def test_decode_base64_errors() -> None:
    with pytest.raises(TypeError):
        decode_base64(123, "field")  # type: ignore


@pytest.mark.parametrize(
    "value, expected",
    [
        (123, "123"),
        (0, "0"),
        (-1, "-1"),
    ],
)
def test_encode_int64(value: int, expected: str) -> None:
    assert encode_int64(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("123", 123),
        (123, 123),
        (None, 0),
    ],
)
def test_decode_int64(value: Optional[Union[int, str]], expected: int) -> None:
    assert decode_int64(value, "field") == expected


def test_decode_int64_errors() -> None:
    with pytest.raises(TypeError):
        decode_int64([], "field")  # type: ignore
    with pytest.raises(ValueError, match="Invalid int64 value"):
        decode_int64("abc", "field")


@pytest.mark.parametrize(
    "value, expected",
    [
        (1.5, 1.5),
        (float("nan"), "NaN"),
        (float("inf"), "Infinity"),
        (float("-inf"), "-Infinity"),
    ],
)
def test_encode_float(value: float, expected: Union[float, str]) -> None:
    result = encode_float(value)
    if isinstance(expected, float) and math.isnan(expected):
        assert math.isnan(result)  # type: ignore
    else:
        assert result == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (1.5, 1.5),
        ("1.5", 1.5),
        (1, 1.0),
        ("NaN", math.nan),
        ("Infinity", math.inf),
        ("-Infinity", -math.inf),
        (None, 0.0),
    ],
)
def test_decode_float(
    value: Optional[Union[float, int, str]], expected: float
) -> None:
    result = decode_float(value, "field")
    if math.isnan(expected):
        assert math.isnan(result)
    else:
        assert result == expected


def test_decode_float_errors() -> None:
    with pytest.raises(TypeError):
        decode_float([], "field")  # type: ignore
    with pytest.raises(ValueError, match="Invalid float value"):
        decode_float("abc", "field")


def test_repeated_fields() -> None:
    values = [1, 2, 3]
    assert encode_repeated(values, str) == ["1", "2", "3"]
    assert encode_repeated([], str) == []
    assert encode_repeated(None, str) == []  # type: ignore

    assert decode_repeated(["1", "2"], int, "field") == [1, 2]
    assert decode_repeated([], int, "field") == []
    assert decode_repeated(None, int, "field") == []


def test_decode_repeated_errors() -> None:
    with pytest.raises(TypeError):
        decode_repeated("not a list", lambda x: x, "field")  # type: ignore


def test_validate_type() -> None:
    validate_type("s", str, "field")
    validate_type(1, int, "field")
    validate_type(1, (int, str), "field")
    validate_type("s", (int, str), "field")

    with pytest.raises(
        TypeError, match="Field 'field' expected <class 'int'>, got str"
    ):
        validate_type("s", int, "field")

    with pytest.raises(
        TypeError,
        match=r"Field 'field' expected \(<class 'int'>, <class 'float'>\), got str",
    ):
        validate_type("s", (int, float), "field")
