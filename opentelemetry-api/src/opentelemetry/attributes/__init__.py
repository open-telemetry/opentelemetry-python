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
# type: ignore

import logging
import threading
from collections import OrderedDict
from collections.abc import MutableMapping
from types import MappingProxyType
from typing import MutableSequence, Optional, Sequence

from opentelemetry.util import types

_VALID_ATTR_VALUE_TYPES = (bool, str, int, float)


_logger = logging.getLogger(__name__)


def _is_valid_attribute_value(value: types.AttributeValue) -> bool:
    """Checks if attribute value is valid.

    An attribute value is valid if it is either:
        - A primitive type: string, boolean, double precision floating
            point (IEEE 754-1985) or integer.
        - An array of primitive type values. The array MUST be homogeneous,
            i.e. it MUST NOT contain values of different types.
    """

    if isinstance(value, Sequence):
        if len(value) == 0:
            return True

        sequence_first_valid_type = None
        for element in value:
            if element is None:
                continue
            element_type = type(element)
            if element_type not in _VALID_ATTR_VALUE_TYPES:
                _logger.warning(
                    "Invalid type %s in attribute value sequence. Expected one of "
                    "%s or None",
                    element_type.__name__,
                    [
                        valid_type.__name__
                        for valid_type in _VALID_ATTR_VALUE_TYPES
                    ],
                )
                return False
            # The type of the sequence must be homogeneous. The first non-None
            # element determines the type of the sequence
            if sequence_first_valid_type is None:
                sequence_first_valid_type = element_type
            elif not isinstance(element, sequence_first_valid_type):
                _logger.warning(
                    "Mixed types %s and %s in attribute value sequence",
                    sequence_first_valid_type.__name__,
                    type(element).__name__,
                )
                return False

    elif not isinstance(value, _VALID_ATTR_VALUE_TYPES):
        _logger.warning(
            "Invalid type %s for attribute value. Expected one of %s or a "
            "sequence of those types",
            type(value).__name__,
            [valid_type.__name__ for valid_type in _VALID_ATTR_VALUE_TYPES],
        )
        return False
    return True


def _filter_attributes(attributes: types.Attributes) -> None:
    """Applies attribute validation rules and drops (key, value) pairs
    that doesn't adhere to attributes specification.

    https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/common/common.md#attributes.
    """
    if attributes:
        for attr_key, attr_value in list(attributes.items()):
            if not attr_key:
                _logger.warning("invalid key `%s` (empty or null)", attr_key)
                attributes.pop(attr_key)
                continue

            if _is_valid_attribute_value(attr_value):
                if isinstance(attr_value, MutableSequence):
                    attributes[attr_key] = tuple(attr_value)
                if isinstance(attr_value, bytes):
                    try:
                        attributes[attr_key] = attr_value.decode()
                    except ValueError:
                        attributes.pop(attr_key)
                        _logger.warning("Byte attribute could not be decoded.")
            else:
                attributes.pop(attr_key)


def _create_immutable_attributes(
    attributes: types.Attributes,
) -> types.Attributes:
    return MappingProxyType(attributes.copy() if attributes else {})


_DEFAULT_LIMIT = 128


class BoundedDict(MutableMapping):
    """An ordered dict with a fixed max capacity.

    Oldest elements are dropped when the dict is full and a new element is
    added.
    """

    def __init__(
        self,
        maxlen: Optional[int] = _DEFAULT_LIMIT,
        attributes: types.Attributes = None,
        immutable: bool = True,
    ):
        if maxlen is not None:
            if not isinstance(maxlen, int):
                raise ValueError
            if maxlen < 0:
                raise ValueError
        self.maxlen = maxlen
        self.dropped = 0
        self._dict = OrderedDict()  # type: OrderedDict
        self._lock = threading.Lock()  # type: threading.Lock
        if attributes:
            _filter_attributes(attributes)
            for key, value in attributes.items():
                self[key] = value
        self._immutable = immutable

    def __repr__(self):
        return "{}({}, maxlen={})".format(
            type(self).__name__, dict(self._dict), self.maxlen
        )

    def __getitem__(self, key):
        return self._dict[key]

    def __setitem__(self, key, value):
        if getattr(self, "_immutable", False):
            raise TypeError
        with self._lock:
            if self.maxlen is not None and self.maxlen == 0:
                self.dropped += 1
                return

            if key in self._dict:
                del self._dict[key]
            elif self.maxlen is not None and len(self._dict) == self.maxlen:
                del self._dict[next(iter(self._dict.keys()))]
                self.dropped += 1
            self._dict[key] = value

    def __delitem__(self, key):
        if getattr(self, "_immutable", False):
            raise TypeError
        del self._dict[key]

    def __iter__(self):
        with self._lock:
            return iter(self._dict.copy())

    def __len__(self):
        return len(self._dict)

    def copy(self):
        return self._dict.copy()
