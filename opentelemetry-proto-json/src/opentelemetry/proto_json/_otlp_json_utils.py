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

import base64
import math
from typing import Any, Callable, List, Optional, TypeVar, Union

T = TypeVar("T")


def encode_hex(value: bytes) -> str:
    """
    Encode bytes as hex string.
    Used for trace_id and span_id per OTLP spec.
    """
    if not value:
        return ""
    return value.hex()


def encode_base64(value: bytes) -> str:
    """
    Encode bytes as base64 string.
    Standard Proto3 JSON mapping for bytes.
    """
    if not value:
        return ""
    return base64.b64encode(value).decode("utf-8")


def encode_int64(value: int) -> str:
    """
    Encode 64-bit integers as strings.
    Required for int64, uint64, fixed64, sfixed64, sint64 per Proto3 JSON spec.
    """
    return str(value)


def encode_float(value: float) -> Union[float, str]:
    """
    Encode float/double values.
    Handles special values NaN, Infinity, -Infinity as strings.
    """
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    return value


def serialize_repeated(
    values: List[Any], map_fn: Callable[[Any], Any]
) -> List[Any]:
    """Helper to serialize repeated fields."""
    if values is None:
        return []
    return [map_fn(v) for v in values]


def decode_hex(value: Optional[str]) -> bytes:
    """Decode hex string to bytes (trace_id, span_id)."""
    if not value:
        return b""
    try:
        return bytes.fromhex(value)
    except ValueError as e:
        raise ValueError(f"Invalid hex string: {e}") from None


def decode_base64(value: Optional[str]) -> bytes:
    """Decode base64 string to bytes."""
    if not value:
        return b""
    try:
        return base64.b64decode(value)
    except Exception as e:
        raise ValueError(f"Invalid base64 string: {e}") from None


def parse_int64(value: Optional[Union[int, str]]) -> int:
    """Parse 64-bit integer from string or number."""
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid int64 value: {value}") from None


def parse_float(value: Optional[Union[float, int, str]]) -> float:
    """Parse float/double from number or special string."""
    if value is None:
        return 0.0
    if value == "NaN":
        return math.nan
    if value == "Infinity":
        return math.inf
    if value == "-Infinity":
        return -math.inf
    try:
        return float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid float value: {value}") from None


def deserialize_repeated(
    values: Optional[List[Any]], item_parser: Callable[[Any], T]
) -> List[T]:
    """Helper to deserialize repeated fields."""
    if not values:
        return []
    return [item_parser(v) for v in values]
