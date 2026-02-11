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

from __future__ import annotations

import base64
import math
import typing

T = typing.TypeVar("T")


def encode_hex(value: bytes) -> str:
    """
    Encode bytes as hex string.
    Used for trace_id and span_id per OTLP spec.
    """
    return value.hex() if value else ""


def encode_base64(value: bytes) -> str:
    """
    Encode bytes as base64 string.
    Standard Proto3 JSON mapping for bytes.
    """
    return base64.b64encode(value).decode("utf-8") if value else ""


def encode_int64(value: int) -> str:
    """
    Encode 64 bit integers as strings.
    Required for int64, uint64, fixed64, sfixed64 and sint64 per Proto3 JSON spec.
    """
    return str(value)


def encode_float(value: float) -> typing.Union[float, str]:
    """
    Encode float/double values.
    """
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    return value


def encode_repeated(
    values: list[typing.Any], map_fn: typing.Callable[[typing.Any], typing.Any]
) -> list[typing.Any]:
    """Helper to serialize repeated fields."""
    return [map_fn(v) for v in values] if values else []


def decode_hex(value: typing.Optional[str], field_name: str) -> bytes:
    """Decode hex string to bytes."""
    if not value:
        return b""
    validate_type(value, str, field_name)
    try:
        return bytes.fromhex(value)
    except ValueError as e:
        raise ValueError(
            f"Invalid hex string for field '{field_name}': {e}"
        ) from None


def decode_base64(value: typing.Optional[str], field_name: str) -> bytes:
    """Decode base64 string to bytes."""
    if not value:
        return b""
    validate_type(value, str, field_name)
    try:
        return base64.b64decode(value)
    except Exception as e:
        raise ValueError(
            f"Invalid base64 string for field '{field_name}': {e}"
        ) from None


def decode_int64(
    value: typing.Optional[typing.Union[int, str]], field_name: str
) -> int:
    """Parse 64-bit integer from string or number."""
    if value is None:
        return 0
    validate_type(value, (int, str), field_name)
    try:
        return int(value)
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid int64 value for field '{field_name}': {value}"
        ) from None


def decode_float(
    value: typing.Optional[typing.Union[float, int, str]], field_name: str
) -> float:
    """Parse float/double from number or special string."""
    if value is None:
        return 0.0
    validate_type(value, (float, int, str), field_name)
    if value == "NaN":
        return math.nan
    if value == "Infinity":
        return math.inf
    if value == "-Infinity":
        return -math.inf
    try:
        return float(value)
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid float value for field '{field_name}': {value}"
        ) from None


def decode_repeated(
    values: typing.Optional[list[typing.Any]],
    item_parser: typing.Callable[[typing.Any], T],
    field_name: str,
) -> list[T]:
    """Helper to deserialize repeated fields."""
    if values is None:
        return []
    validate_type(values, list, field_name)
    return [item_parser(v) for v in values]


def validate_type(
    value: typing.Any,
    expected_types: typing.Union[type, tuple[type, ...]],
    field_name: str,
) -> None:
    """
    Validate that a value is of the expected type(s).
    Raises TypeError if validation fails.
    """
    if not isinstance(value, expected_types):
        raise TypeError(
            f"Field '{field_name}' expected {expected_types}, "
            f"got {type(value).__name__}"
        )
