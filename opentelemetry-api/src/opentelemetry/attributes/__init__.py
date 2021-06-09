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
    _filter_attributes(attributes)
    return MappingProxyType(attributes.copy() if attributes else {})


class _BoundedDict(MutableMapping):
    """An ordered dict with a fixed max capacity.

    Oldest elements are dropped when the dict is full and a new element is
    added.
    """

    def __init__(
        self, maxlen: Optional[int], immutable: Optional[bool] = False
    ):
        if maxlen is not None:
            if not isinstance(maxlen, int):
                raise ValueError
            if maxlen < 0:
                raise ValueError
        self.maxlen = maxlen
        self._immutable = immutable
        self.dropped = 0
        self._dict = OrderedDict()  # type: OrderedDict
        self._lock = threading.Lock()  # type: threading.Lock

    def __repr__(self):
        return "{}({}, maxlen={})".format(
            type(self).__name__, dict(self._dict), self.maxlen
        )

    def __getitem__(self, key):
        return self._dict[key]

    def __setitem__(self, key, value):
        if self._immutable:
            raise TypeError()
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
        if self._immutable:
            raise TypeError()
        del self._dict[key]

    def __iter__(self):
        with self._lock:
            return iter(self._dict.copy())

    def __len__(self):
        return len(self._dict)

    def copy(self):
        return self._dict.copy()

    @classmethod
    def from_map(cls, maxlen, immutable, mapping):
        mapping = OrderedDict(mapping)
        bounded_dict = cls(maxlen)
        for key, value in mapping.items():
            bounded_dict[key] = value
        bounded_dict._immutable = immutable  # pylint: disable=protected-access
        return bounded_dict


class Attributed:
    """The Attributed class is extended by all components
    that provide attributes as part of their data models.
    """

    def __init__(
        self,
        attributes: types.Attributes = None,
        filtered: bool = False,
        limit: int = 128,  # TODO: this should not be hardcoded here
        immutable: bool = False,
    ) -> None:
        if filtered:
            _filter_attributes(attributes)
        if attributes is None:
            self._attributes = _BoundedDict(limit, immutable)
        else:
            self._attributes = _BoundedDict.from_map(
                limit, immutable, attributes
            )

    @property
    def attributes(self) -> types.Attributes:
        return self._attributes

    @property
    def dropped_attributes(self) -> int:
        if self._attributes:
            return self._attributes.dropped
        return 0
