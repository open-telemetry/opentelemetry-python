# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import copy
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Literal

from opentelemetry.util import types


class _InvalidAttributeValue(Enum):
    INVALID_VALUE = 1


class _DuplicateFilter(logging.Filter):
    """Filter out potentially noisy logs"""

    def filter(self, record):
        current_log = (
            record.module,
            record.levelno,
            record.lineno,
            time.time() // 60,
        )
        if current_log != getattr(self, "last_log", None):
            self.last_log = current_log  # pylint: disable=attribute-defined-outside-init
            return True
        # False means python's `logging` module will no longer process this log.
        return False


_logger = logging.getLogger(__name__)
_logger.addFilter(_DuplicateFilter())


def _clean_attribute_value(
    value: types.AttributeValue, max_string_value_length: int | None
) -> types.AttributeValue | Literal[_InvalidAttributeValue.INVALID_VALUE]:
    """Recursively checks if an attribute value is valid and cleans it if required.

    Bytes are decoded to strings via utf-8, and removed if decoding fails.
    String values are truncated to max_string_value_length if provided.
    Anything that isn't of `types.AttributeValue` is removed.

    Returns:
        _InvalidAttributeValue.INVALID_VALUE if the value is removed and otherwise
        returns the cleaned value.
    """
    if isinstance(value, (type(None), bool, int, float)):
        return value
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            _logger.exception(
                "Invalid byte sequence for attribute value, dropping value from attribute."
            )
            return _InvalidAttributeValue.INVALID_VALUE
    if isinstance(value, str):
        if (
            max_string_value_length is not None
            and len(value) > max_string_value_length
        ):
            _logger.warning(
                "String attribute value exceeds max length of %d, truncating.",
                max_string_value_length,
            )
            value = value[:max_string_value_length]
        return value
    if isinstance(value, Sequence):
        cleaned_sequence = []
        for v in value:
            # Drop invalid values.
            if (
                cleaned_value := _clean_attribute_value(
                    v, max_string_value_length
                )
            ) != _InvalidAttributeValue.INVALID_VALUE:
                cleaned_sequence.append(cleaned_value)
        return tuple(cleaned_sequence)
    if isinstance(value, Mapping):
        cleaned_mapping = {}
        for key, val in value.items():
            # skip invalid keys
            if not key or not isinstance(key, str):
                _logger.warning(
                    "invalid key `%s` inside an attribute value. Must be non-empty string, dropping key/value pair.",
                    key,
                )
                continue
            if (
                cleaned_value := _clean_attribute_value(
                    val, max_string_value_length
                )
            ) != _InvalidAttributeValue.INVALID_VALUE:
                cleaned_mapping[key] = cleaned_value
        return cleaned_mapping
    _logger.warning(
        "Invalid type %s for attribute value. Expected one of bool, str, None, bytes, int, float or a "
        "Mapping or Sequence of those types. Attempting to cast type to string, value will be dropped if that fails.",
        type(value),
    )
    try:
        return str(value)
    except Exception:
        return _InvalidAttributeValue.INVALID_VALUE


class BoundedAttributes(OrderedDict):  # type: ignore
    """An ordered dict with a fixed max capacity.

    Oldest elements are dropped when the dict is full and a new element is
    added.
    """

    def __init__(
        self,
        maxlen: int | None = None,
        attributes: types.Attributes = None,
        immutable: bool = True,
        max_value_len: int | None = None,
        extended_attributes: bool = True,
    ):
        if maxlen is not None:
            if not isinstance(maxlen, int) or maxlen < 0:
                raise ValueError(
                    "maxlen must be valid int greater or equal to 0"
                )
        self.maxlen = maxlen
        self.dropped = 0
        self.max_value_len = max_value_len
        self._dict: OrderedDict[str, types.AnyValue] = OrderedDict()
        self._lock = threading.RLock()
        self._immutable = False
        if attributes:
            for key, value in attributes.items():
                self[key] = value
        self._immutable = immutable

    def __repr__(self) -> str:
        return f"{dict(self._dict)}"

    def __getitem__(self, key: str) -> types.AnyValue:
        return self._dict[key]

    def __setitem__(self, key: str, value: types.AnyValue) -> None:
        if self._immutable:
            raise TypeError
        with self._lock:
            if self.maxlen == 0:
                self.dropped += 1
                return
            if not key or not isinstance(key, str):
                _logger.warning(
                    "invalid key `%s`. must be non-empty string. Dropping key from attributes.",
                    key,
                )
                self.dropped += 1
                return
            cleaned_value = _clean_attribute_value(value, self.max_value_len)
            if cleaned_value is _InvalidAttributeValue.INVALID_VALUE:
                _logger.warning(
                    "Invalid value `%s` for key `%s`. Dropping this key-value pair from attributes.",
                    value,
                    key,
                )
                self.dropped += 1
                return
            if key in self._dict:
                _logger.warning(
                    "Key `%s` already exists in attributes. Overwriting value with new value.",
                    key,
                )
                del self._dict[key]
            if len(self._dict) == self.maxlen:
                _logger.warning(
                    "Attributes dict is full. Dropping the oldest key-value pair from attributes to make space for the new key-value pair.",
                )
                self._dict.popitem(last=False)
                self.dropped += 1

            self._dict[key] = value

    def __delitem__(self, key: str) -> None:
        if self._immutable:
            raise TypeError
        with self._lock:
            del self._dict[key]

    def __iter__(self):
        with self._lock:
            return iter(self._dict.copy())

    def __len__(self) -> int:
        return len(self._dict)

    def __deepcopy__(self, memo: dict) -> "BoundedAttributes":
        copy_ = BoundedAttributes(
            maxlen=self.maxlen,
            immutable=self._immutable,
            max_value_len=self.max_value_len,
            extended_attributes=True,
        )
        memo[id(self)] = copy_
        with self._lock:
            # Assign _dict directly to avoid re-cleaning already clean values
            # and to bypass the immutability guard in __setitem__
            copy_._dict = copy.deepcopy(self._dict, memo)
            copy_.dropped = self.dropped
        return copy_

    def copy(self):  # type: ignore
        return self._dict.copy()  # type: ignore
