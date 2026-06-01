# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import copy
import logging
import threading
import time
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


def _clean_attribute_value(  # pylint: disable=too-many-return-statements,too-many-branches
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
        for val in value:
            # Drop invalid values.
            if (
                cleaned_value := _clean_attribute_value(
                    val, max_string_value_length
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
    except Exception:  # pylint: disable=broad-exception-caught
        return _InvalidAttributeValue.INVALID_VALUE


class BoundedAttributes(dict):
    """A dict with a fixed max capacity which cleans values to ensure they are valid attribute values.

    When the dict is full and a new element is added, the oldest element is dropped.
    """

    def __init__(
        self,
        maxlen: int | None = None,
        attributes: types.Attributes = None,
        immutable: bool = True,
        max_value_len: int | None = None,
        extended_attributes: bool = False,  # No longer used.. etended attributes are always used. Here for backward compatibility.
        disable_cleaning_and_immutability_for_copy: bool = False,
    ):
        if maxlen is not None:
            if not isinstance(maxlen, int) or maxlen < 0:
                raise ValueError(
                    "maxlen must be valid int greater or equal to 0"
                )
        dict.__init__(self)
        self.disable_cleaning_and_immutability_for_copy = (
            disable_cleaning_and_immutability_for_copy
        )
        self.maxlen = maxlen
        self.dropped = 0
        self.max_value_len = max_value_len
        self._lock = threading.RLock()
        self._immutable = False
        if attributes:
            for key, value in attributes.items():
                self[key] = value
        self._immutable = immutable

    def __setitem__(self, key: str, value: types.AnyValue) -> None:
        if self.disable_cleaning_and_immutability_for_copy:
            dict.__setitem__(self, key, value)
            return
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
            if key in self:
                _logger.warning(
                    "Key `%s` already exists in attributes. Overwriting value with new value.",
                    key,
                )
                dict.__delitem__(self, key)
            if self.maxlen and len(self) >= self.maxlen:
                _logger.warning(
                    "Attributes dict is full. Dropping the oldest key-value pair from attributes to make space for the new key-value pair.",
                )
                # In python 3.7+ dictionaries are ordered, this is the recommended way to get the oldest value.
                first_key = next(iter(self.keys()))
                self.pop(first_key)
                self.dropped += 1

            dict.__setitem__(self, key, cleaned_value)

    def __delitem__(self, key: str) -> None:
        if self._immutable:
            raise TypeError
        with self._lock:
            dict.__delitem__(self, key)

    def __iter__(self):
        with self._lock:
            return iter(self.copy())

    def __deepcopy__(self, memo: dict) -> "BoundedAttributes":
        with self._lock:
            copy_ = BoundedAttributes(
                maxlen=self.maxlen,
                attributes=copy.deepcopy(self.copy(), memo),
                immutable=self._immutable,
                max_value_len=self.max_value_len,
                extended_attributes=True,
                disable_cleaning_and_immutability_for_copy=True,
            )
            memo[id(self)] = copy_
            # Assign _dict directly to avoid re-cleaning already clean values
            # and to bypass the immutability guard in __setitem__
            copy_.dropped = self.dropped
            copy_.disable_cleaning_and_immutability_for_copy = False
            return copy_

    # Python's dict.update doesn't call setitem. We are overwriting this method to make sure it does..
    def update(self, *args, **kwargs):
        with self._lock:
            for key, val in dict(*args, **kwargs).items():
                self[key] = val
