# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import abc
import base64
import collections.abc
import enum
import json
import math
import typing

T = typing.TypeVar("T")
M = typing.TypeVar("M", bound="JsonMessage")
EnumT = typing.TypeVar("EnumT", bound=enum.IntEnum)


class JsonMessage(abc.ABC):
    """
    Abstract base class for protobuf messages with JSON serialization.
    """

    @abc.abstractmethod
    def to_dict(self) -> dict[str, typing.Any]:
        """
        Convert this message to a dictionary.
        """

    @classmethod
    @abc.abstractmethod
    def from_dict(cls: type[M], data: dict[str, typing.Any]) -> M:
        """
        Create an instance from a dictionary.
        """

    def to_json(self) -> str:
        """
        Serialize this message to a JSON string.
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls: type[M], data: str | bytes) -> M:
        """
        Deserialize from a JSON string or bytes.
        """
        return cls.from_dict(json.loads(data))


def encode_hex(value: bytes | None) -> str:
    """
    Encode bytes as hex string.

    Args:
        value: The bytes to encode.
    Returns:
        Hex string representation of the input bytes.
    """
    return value.hex() if value else ""


def encode_base64(value: bytes | None) -> str:
    """
    Encode bytes as base64 string.
    Standard Proto3 JSON mapping for bytes.

    Args:
        value: The bytes to encode.
    Returns:
        Base64 string representation of the input bytes.
    """
    return base64.b64encode(value).decode("utf-8") if value else ""


def encode_int64(value: int) -> str:
    """
    Encode 64 bit integers as strings.
    Required for int64, uint64, fixed64, sfixed64 and sint64 per Proto3 JSON spec.

    Args:
        value: The integer to encode.
    Returns:
        String representation of the input integer.
    """
    return str(value)


def encode_float(value: float) -> float | str:
    """
    Encode float/double values.

    Args:
        value: The float to encode.
    Returns:
        The input value, or a string for special float values (NaN, Infinity).
    """
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    return value


def encode_repeated(
    values: list[T] | None,
    map_fn: collections.abc.Callable[[T], typing.Any],
) -> list[typing.Any]:
    """
    Helper to serialize repeated fields with a mapping function.

    Args:
        values: The list of values to encode.
        map_fn: A function that takes a single value and returns its encoded form.
    Returns:
        A list of encoded values, or an empty list if input is None or empty.
    """
    return [map_fn(v) for v in values] if values else []


def decode_hex(value: str | None, field_name: str) -> bytes:
    """
    Decode hex string to bytes.

    Args:
        value: The hex string to decode.
        field_name: The name of the field being decoded (for error messages).
    Returns:
        The decoded bytes, or empty bytes if input is None or empty.
    """
    if not value:
        return b""
    validate_type(value, str, field_name)
    try:
        return bytes.fromhex(value)
    except ValueError as error:
        raise ValueError(
            f"Invalid hex string for field '{field_name}': {error}"
        ) from None


def decode_base64(value: str | None, field_name: str) -> bytes:
    """
    Decode base64 string to bytes.

    Args:
        value: The base64 string to decode.
        field_name: The name of the field being decoded (for error messages).
    Returns:
        The decoded bytes, or empty bytes if input is None or empty.
    """
    if not value:
        return b""
    validate_type(value, str, field_name)
    try:
        return base64.b64decode(value)
    except Exception as error:
        raise ValueError(
            f"Invalid base64 string for field '{field_name}': {error}"
        ) from None


def decode_int64(value: int | str | None, field_name: str) -> int:
    """
    Parse int64 from number or string.

    Args:
        value: The value to decode, which can be an int, a string, or None
        field_name: The name of the field being decoded (for error messages).
    Returns:
        The decoded integer, or 0 if input is None.
    """
    if value is None:
        return 0
    validate_type(value, (int, str), field_name)
    try:
        return int(value)
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid int64 value for field '{field_name}': {value}"
        ) from None


def decode_float(value: float | int | str | None, field_name: str) -> float:
    """
    Parse float/double from number or string, handling special values.

    Args:
        value: The value to decode, which can be a float, int, string, or None
        field_name: The name of the field being decoded (for error messages).
    Returns:
        The decoded float, or 0.0 if input is None.
    """
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
    values: list[typing.Any] | None,
    item_parser: collections.abc.Callable[[typing.Any], T],
    field_name: str,
) -> list[T]:
    """
    Parse a list of values using the provided item parser function.

    Args:
        values: The list of values to decode, or None.
        item_parser: A function that takes a single value and returns the parsed form.
        field_name: The name of the field being decoded (for error messages).
    Returns:
        A list of parsed values, or an empty list if input is None.
    """
    if values is None:
        return []
    validate_type(values, list, field_name)
    return [item_parser(v) for v in values]


def validate_type(
    value: typing.Any,
    expected_types: type | tuple[type, ...],
    field_name: str,
) -> None:
    """
    Validate that a value is of the expected type(s).
    Raises TypeError if validation fails.

    Args:
        value: The value to validate.
        expected_types: A type or tuple of types that the value is expected to be.
        field_name: The name of the field being validated (for error messages).
    """
    if not isinstance(value, expected_types):
        raise TypeError(
            f"Field '{field_name}' expected {expected_types}, "
            f"got {type(value).__name__}"
        )


def decode_enum(
    value: typing.Any,
    enum_type: type[EnumT],
    field_name: str,
) -> EnumT:
    """
    Decode a JSON enum value into an enum member.

    Per the ProtoJSON spec, parsers must accept both enum names (str)
    and integer values (int).

    Args:
        value: The enum name or integer value to decode.
        enum_type: The enum class to decode into.
        field_name: The name of the field being decoded (for error messages).
    Returns:
        The corresponding enum member.
    """
    if isinstance(value, bool):
        raise TypeError(f"Field '{field_name}' expected int or str, got bool")
    validate_type(value, (int, str), field_name)
    if isinstance(value, str):
        try:
            return enum_type[value]
        except KeyError:
            raise KeyError(
                f"Invalid enum name '{value}' for field '{field_name}'"
            ) from None
    try:
        return enum_type(value)
    except ValueError:
        raise ValueError(
            f"Invalid enum value {value} for field '{field_name}'"
        ) from None
