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

import datetime
import logging
import threading
from collections import OrderedDict, deque
from collections.abc import MutableMapping, Sequence
from types import MappingProxyType
from typing import MutableSequence

from opentelemetry.util import types

_VALID_ATTR_VALUE_TYPES = (bool, str, int, float)


_logger = logging.getLogger(__name__)


def _is_valid_attribute_value(value: types.AttributeValue) -> bool:
    """Checks if attribute value is valid.

    An attribute value is valid if it is one of the valid types.
    If the value is a sequence, it is only valid if all items in the sequence:
      - are of the same valid type or None
      - are not a sequence
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


def _filter_attributes(attributes: types.Attributes):
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
                        _logger.warning("Byte attribute could not be decoded.")
            else:
                attributes.pop(attr_key)


def _create_immutable_attributes(attributes):
    return MappingProxyType(attributes.copy() if attributes else {})


def ns_to_iso_str(nanoseconds):
    """Get an ISO 8601 string from time_ns value."""
    ts = datetime.datetime.utcfromtimestamp(nanoseconds / 1e9)
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def get_dict_as_key(labels):
    """Converts a dict to be used as a unique key"""
    return tuple(
        sorted(
            map(
                lambda kv: (kv[0], tuple(kv[1]))
                if isinstance(kv[1], list)
                else kv,
                labels.items(),
            )
        )
    )


class BoundedList(Sequence):
    """An append only list with a fixed max size.

    Calls to `append` and `extend` will drop the oldest elements if there is
    not enough room.
    """

    def __init__(self, maxlen):
        self.dropped = 0
        self._dq = deque(maxlen=maxlen)  # type: deque
        self._lock = threading.Lock()

    def __repr__(self):
        return "{}({}, maxlen={})".format(
            type(self).__name__, list(self._dq), self._dq.maxlen
        )

    def __getitem__(self, index):
        return self._dq[index]

    def __len__(self):
        return len(self._dq)

    def __iter__(self):
        with self._lock:
            return iter(deque(self._dq))

    def append(self, item):
        with self._lock:
            if len(self._dq) == self._dq.maxlen:
                self.dropped += 1
            self._dq.append(item)

    def extend(self, seq):
        with self._lock:
            to_drop = len(seq) + len(self._dq) - self._dq.maxlen
            if to_drop > 0:
                self.dropped += to_drop
            self._dq.extend(seq)

    @classmethod
    def from_seq(cls, maxlen, seq):
        seq = tuple(seq)
        if len(seq) > maxlen:
            raise ValueError
        bounded_list = cls(maxlen)
        # pylint: disable=protected-access
        bounded_list._dq = deque(seq, maxlen=maxlen)
        return bounded_list


class BoundedDict(MutableMapping):
    """An ordered dict with a fixed max capacity.

    Oldest elements are dropped when the dict is full and a new element is
    added.
    """

    def __init__(self, maxlen):
        if not isinstance(maxlen, int):
            raise ValueError
        if maxlen < 0:
            raise ValueError
        self.maxlen = maxlen
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
        with self._lock:
            if self.maxlen == 0:
                self.dropped += 1
                return

            if key in self._dict:
                del self._dict[key]
            elif len(self._dict) == self.maxlen:
                del self._dict[next(iter(self._dict.keys()))]
                self.dropped += 1
            self._dict[key] = value

    def __delitem__(self, key):
        del self._dict[key]

    def __iter__(self):
        with self._lock:
            return iter(self._dict.copy())

    def __len__(self):
        return len(self._dict)

    @classmethod
    def from_map(cls, maxlen, mapping):
        mapping = OrderedDict(mapping)
        if len(mapping) > maxlen:
            raise ValueError
        bounded_dict = cls(maxlen)
        # pylint: disable=protected-access
        bounded_dict._dict = mapping
        return bounded_dict
