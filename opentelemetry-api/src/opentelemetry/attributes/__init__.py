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

import logging
import threading
from collections import OrderedDict
from collections.abc import MutableMapping
from typing import Any, Mapping, Optional, Sequence, Union

from opentelemetry.util import types

# bytes are accepted as a user supplied value for attributes but
# decoded to strings internally.
_PRIMITIVE_ATTRIBUTES = (bool, str, bytes, int, float)
# AnyValue possible values
_VALID_ANY_VALUE_TYPES = (
    type(None),
    bool,
    bytes,
    int,
    float,
    str,
    Sequence,
    Mapping,
)

_logger = logging.getLogger(__name__)


def _is_homogeneous_list_of_primitives(value: Sequence) -> tuple[bool, type]:
    if len(value) == 0:
        return (True, None)

    first_type = None  # type: Optional[type]
    for v in value:
        if not v:
            continue
        if first_type is None:
            first_type = type(v)
        else:
            if not isinstance(v, first_type):
                return (False, None)
            if not isinstance(v, _PRIMITIVE_ATTRIBUTES):
                return (False, None)
    return (True, first_type)


def _clean_extended_attribute(
    key: str, value: types.AnyValue, max_value_len: Optional[int]
) -> tuple[types.AnyValue, bool]:
    """Checks if attribute value is valid and cleans it if required.

    The function returns the cleaned value or None if the value is not valid.

    An attribute value is valid if it is an AnyValue.
    An attribute needs cleansing if:
        - Its length is greater than the maximum allowed length.
    """

    if not (key and isinstance(key, str)):
        _logger.warning("invalid key `%s`. must be non-empty string.", key)
        return (None, False)

    try:
        return _clean_extended_attribute_value(
            value, max_value_len=max_value_len
        )
    except TypeError as exception:
        _logger.warning(
            f"Error processing attribute {key}", exc_info=exception
        )
        return (None, False)


def _clean_extended_attribute_value(
    value: types.AnyValue, max_value_len: Optional[int]
) -> tuple[types.AnyValue, bool]:
    if value is None or isinstance(value, _PRIMITIVE_ATTRIBUTES):
        # keeping b'string' backwards compatible with old standard
        # attribute behavior. It also keeps it consistent
        # across different attribute flavors.
        if isinstance(value, bytes):
            try:
                return _clean_extended_attribute_value(
                    value.decode(), max_value_len=max_value_len
                )
            except UnicodeDecodeError:
                pass

        if max_value_len is not None and isinstance(value, str):
            return (value[:max_value_len], True)

        return (value, True)

    if isinstance(value, Sequence):
        if max_value_len is None:
            (is_homogeneous, value_type) = _is_homogeneous_list_of_primitives(
                value
            )
            if (
                is_homogeneous
                and value_type is not str
                and value_type is not bytes
            ):
                return (tuple(value), True)

        return (
            (
                tuple(
                    [
                        _clean_extended_attribute_value(
                            v, max_value_len=max_value_len
                        )[0]
                        for v in value
                    ]
                )
            ),
            True,
        )

    if isinstance(value, Mapping):
        cleaned_list = []
        for k, v in value.items():
            if not (k and isinstance(k, str)):
                continue

            cleaned_list.append(
                (
                    k,
                    _clean_extended_attribute_value(
                        v, max_value_len=max_value_len
                    )[0],
                )
            )

        return (OrderedDict(sorted(cleaned_list)), True)

    _logger.warning(
        "Attribute value %s is not valid. Must be one of %s",
        value,
        _VALID_ANY_VALUE_TYPES,
    )
    return (None, False)


def _count_leaves(value: types.AnyValue) -> int:
    # it should be possible to optimize if we have a dedicated type for
    # AnyValue and have leaf_count as a property of the type.
    # but we don't expect attributes with huge number of leaves
    # and recommend to use flat attributes whenever possible,
    # so performance in case of the complex value is not a priority.
    if (
        value is None
        or isinstance(value, _PRIMITIVE_ATTRIBUTES)
        or isinstance(value, Sequence)
    ):
        return 1

    if isinstance(value, Mapping):
        leaf_count = 0

        for v in value.values():
            leaf_count += _count_leaves(v)

        return max(1, leaf_count)

    return 0


class BoundedAttributes(MutableMapping):  # type: ignore
    """An ordered dict with a fixed max capacity.

    Oldest elements are dropped when the dict is full and a new element is
    added.
    """

    def __init__(
        self,
        maxlen: Optional[int] = None,
        attributes: Optional[types.Attributes] = None,
        immutable: bool = True,
        max_value_len: Optional[int] = None,
        extended_attributes: bool = True,
    ):
        if maxlen is not None:
            if not isinstance(maxlen, int) or maxlen < 0:
                raise ValueError(
                    "maxlen must be valid int greater or equal to 0"
                )
        self.maxlen = maxlen
        self.dropped = 0
        self.leaf_count = 0
        self.max_value_len = max_value_len
        # OrderedDict is not used until the maxlen is reached for efficiency.

        self._dict: Union[
            MutableMapping[str, types.AnyValue],
            OrderedDict[str, types.AnyValue],
        ] = {}
        self._lock = threading.RLock()
        if attributes:
            for key, value in attributes.items():
                self[key] = value
        self._immutable = immutable

    def __repr__(self) -> str:
        return f"{dict(self._dict)}"

    def __getitem__(self, key: str) -> types.AnyValue:
        return self._dict[key]

    def __setitem__(self, key: str, value: types.AnyValue) -> None:
        if getattr(self, "_immutable", False):  # type: ignore
            raise TypeError
        with self._lock:
            if self.maxlen is not None and self.maxlen == 0:
                self.dropped += 1
                return

            (cleaned_value, is_valid) = _clean_extended_attribute(
                key, value, self.max_value_len
            )

            if not is_valid:
                return

            leafs = _count_leaves(cleaned_value)

            if (
                self.maxlen
                and isinstance(cleaned_value, Mapping)
                and (self.leaf_count + leafs > self.maxlen)
            ):
                self.dropped += 1
                return

            if key in self._dict:
                self._update_count_drop(self._dict.pop(key))
            elif (
                self.maxlen is not None
                and (self.leaf_count + leafs) > self.maxlen
            ):
                if not isinstance(self._dict, OrderedDict):
                    self._dict = OrderedDict(self._dict)
                item = self._dict.popitem(last=False)  # type: ignore
                self._update_count_drop(item[1])
                self.dropped += 1

            self._dict[key] = cleaned_value  # type: ignore
            self.leaf_count += leafs

    def _update_count_drop(self, val: Any) -> None:
        self.leaf_count -= _count_leaves(val)

    def __delitem__(self, key: str) -> None:
        if getattr(self, "_immutable", False):  # type: ignore
            raise TypeError
        with self._lock:
            self._update_count_drop(self._dict.pop(key))

    def __iter__(self):  # type: ignore
        with self._lock:
            return iter(self._dict.copy())  # type: ignore

    def __len__(self) -> int:
        return len(self._dict)

    def copy(self):  # type: ignore
        return self._dict.copy()  # type: ignore
