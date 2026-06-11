# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import copy
import logging
import threading
import time
from collections.abc import Mapping, MutableMapping, Sequence
from types import MappingProxyType
from typing import overload

from typing_extensions import deprecated

from opentelemetry.util import types


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


def _clean_attribute_value(  # pylint: disable=too-many-return-statements
    value: types.AttributeValue,
    max_string_value_length: int | None,
) -> types.AttributeValue:
    """Recursively checks if an attribute value is valid and cleans it if required.

    Byte values are attempted to be decoded to strings using utf-8. If it fails it is left as bytes.
    String values are truncated to max_string_value_length if provided.
    Anything that isn't of `types.AttributeValue`, we attempt to cast to `str`.
    If this fails, the value is replaced with None. Sequence's are converted to tuples and mappings
    are converted to MappingProxyType, these are immutable data structures, so if the sequence/map
    is modified outside of this method, it will not affect the value in this container.

    Returns:
        The recursively cleaned AttributeValue.
    """
    if isinstance(value, (type(None), bool, int, float)):
        return value
    if isinstance(value, bytes):
        # Attempt to decode bytes into a string using utf-8.
        # If it fails just leave it as is, as bytes is a valid attribute value type.
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            return value
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
        return tuple(
            _clean_attribute_value(v, max_string_value_length) for v in value
        )
    if isinstance(value, Mapping):
        cleaned_mapping = {}
        for key, val in value.items():
            if not isinstance(key, str):
                _logger.warning(
                    "invalid key `%s` inside an attribute value mapping. Must be a string. Will attempt to cast to a string via the __str__ method, will drop the key/value pair if that fails.",
                    key,
                )
                try:
                    key = str(key)
                except Exception:
                    continue
            cleaned_mapping[key] = _clean_attribute_value(
                val, max_string_value_length
            )
        return MappingProxyType(cleaned_mapping)
    _logger.warning(
        "Invalid type `%s` for attribute value. Expected one of bool, str, None, bytes, int, float or a "
        "Mapping or Sequence of those types. Value's __str__ method will be called if it exists, otherwise the value will be replaced with None.",
        type(value),
    )
    # Spec says to convert unknown types to strings if possible.
    try:
        return str(value)
    except Exception:
        # Fallback to None in accordance with the OpenTelemetry semantic conventions specification, which is converted to an empty AnyType by the OTLP encoder.
        return None


class BoundedAttributes(MutableMapping):
    """A dict with a fixed max capacity which cleans and potentially drops values to ensure they are valid attribute values.

    Args:
        maxlen: The maximum number of attributes to store.
        attributes: The initial attributes to store.
        immutable: Defaults to true. Whether to allow adding/removing of attributes after the initialisation of the instance.
        max_value_len: The maximum length of string values.
        extended_attributes: Deprecated. Kept for backwards compatibility. Extended attributes are now always used for attributes everywhere.

    When the dict is full and a new element is added, the oldest element is dropped. Attributes are made to be immutable when set in this container.
    So passing a mutable list as an attribute value, and then mutating it after will not change it's value in this container.
    """

    @overload
    def __init__(
        self,
        maxlen: int | None = None,
        attributes: types.Attributes = None,
        immutable: bool = True,
        max_value_len: int | None = None,
    ) -> None: ...

    @overload
    @deprecated(
        "Creating BoundedAttributes with `extended_attributes` set is deprecated. "
        "The `extended_attributes` param is no longer used and will be removed "
        "in a future release. Extended attributes are now always used for attributes everywhere."
    )
    def __init__(
        self,
        maxlen: int | None = None,
        attributes: types.Attributes = None,
        immutable: bool = True,
        max_value_len: int | None = None,
        extended_attributes: bool = False,
    ) -> None: ...

    def __init__(
        self,
        maxlen: int | None = None,
        attributes: types.Attributes = None,
        immutable: bool = True,
        max_value_len: int | None = None,
        extended_attributes: bool = False,
    ) -> None:
        if maxlen is not None:
            if not isinstance(maxlen, int) or maxlen < 0:
                raise ValueError(
                    "maxlen must be valid int greater or equal to 0"
                )
        self._dict = {}
        self.maxlen = maxlen
        self.dropped = 0
        self.max_value_len = max_value_len
        self._lock = threading.RLock()
        self._immutable = False
        if attributes:
            for key, value in attributes.items():
                self[key] = value
        self._immutable = immutable

    def __repr__(self) -> str:
        return f"{dict(self._dict)}"

    def __getitem__(self, key: str) -> types.AttributeValue:
        with self._lock:
            return self._dict[key]

    def __setitem__(self, key: str, value: types.AnyValue) -> None:
        if self._immutable:
            raise TypeError(
                "Cannot mutate this instance, as it was created with immutable=True."
            )
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
            if key in self._dict:
                del self._dict[key]
            if self.maxlen and len(self) >= self.maxlen:
                _logger.warning(
                    "Attributes dict is full. Dropping the oldest key-value pair from attributes to make space for the new key-value pair.",
                )
                # In python 3.7+ dictionaries are ordered, this is the recommended way to get the oldest value.
                del self._dict[next(iter(self._dict.keys()))]
                self.dropped += 1

            self._dict[key] = _clean_attribute_value(value, self.max_value_len)

    def __delitem__(self, key: str) -> None:
        if self._immutable:
            raise TypeError(
                "Cannot mutate this instance, as it was created with immutable=True."
            )
        with self._lock:
            del self._dict[key]

    def __iter__(self):
        with self._lock:
            return iter(list(self._dict.keys()))

    def __len__(self) -> int:
        with self._lock:
            return len(self._dict)

    def __deepcopy__(self, memo: dict) -> "BoundedAttributes":
        copy_ = BoundedAttributes(
            maxlen=self.maxlen,
            immutable=self._immutable,
            max_value_len=self.max_value_len,
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
