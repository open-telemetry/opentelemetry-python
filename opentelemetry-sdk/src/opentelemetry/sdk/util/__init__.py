# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import copy
import datetime
import threading
from collections import deque
from collections.abc import (
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Sequence,
)
from typing import Any, TypeVar, overload

from typing_extensions import deprecated

_T = TypeVar("_T")
_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


def ns_to_iso_str(nanoseconds: int) -> str:
    """Get an ISO 8601 string from time_ns value."""
    ts = datetime.datetime.fromtimestamp(nanoseconds / 1e9, tz=datetime.timezone.utc)
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def get_dict_as_key(labels: Mapping[str, Any]) -> tuple[tuple[str, Any], ...]:
    """Converts a dict to be used as a unique key"""
    return tuple(
        sorted(
            map(
                lambda kv: (kv[0], tuple(kv[1])) if isinstance(kv[1], list) else kv,
                labels.items(),
            )
        )
    )


class BoundedList(Sequence[_T]):
    """An append only list with a fixed max size.

    Calls to `append` and `extend` will drop the oldest elements if there is
    not enough room.
    """

    dropped: int

    def __init__(self, maxlen: int | None):
        self.dropped: int = 0
        self._dq: deque[_T] = deque(maxlen=maxlen)
        self._lock: threading.Lock = threading.Lock()

    def __deepcopy__(self, memo: dict[int, Any]) -> "BoundedList[_T]":
        copy_ = BoundedList(0)
        memo[id(self)] = copy_
        with self._lock:
            copy_.dropped = self.dropped
            copy_._dq = copy.deepcopy(self._dq, memo)
        return copy_

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self._dq)}, maxlen={self._dq.maxlen})"

    @overload
    def __getitem__(self, index: int) -> _T: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[_T]: ...

    def __getitem__(self, index: int | slice) -> _T | Sequence[_T]:
        if isinstance(index, slice):
            return list(self._dq)[index]
        return self._dq[index]

    def __len__(self) -> int:
        return len(self._dq)

    def __iter__(self) -> Iterator[_T]:
        with self._lock:
            return iter(list(self._dq))

    def append(self, item: _T) -> None:
        with self._lock:
            if self._dq.maxlen is not None and len(self._dq) == self._dq.maxlen:
                self.dropped += 1
            self._dq.append(item)

    def extend(self, seq: Sequence[_T]) -> None:
        with self._lock:
            if self._dq.maxlen is not None:
                to_drop = len(seq) + len(self._dq) - self._dq.maxlen
                if to_drop > 0:
                    self.dropped += to_drop
            self._dq.extend(seq)

    @classmethod
    def from_seq(cls: type["BoundedList[_T]"], maxlen: int | None, seq: Iterable[_T]) -> "BoundedList[_T]":
        seq = tuple(seq)
        bounded_list = cls(maxlen)
        bounded_list.extend(seq)
        return bounded_list


@deprecated("Deprecated since version 1.4.0.")
class BoundedDict(MutableMapping[_KT, _VT]):
    """An ordered dict with a fixed max capacity.

    Oldest elements are dropped when the dict is full and a new element is
    added.
    """

    dropped: int
    maxlen: int | None

    def __init__(self, maxlen: int | None):
        if maxlen is not None:
            if not isinstance(maxlen, int):
                raise ValueError
            if maxlen < 0:
                raise ValueError
        self.maxlen: int | None = maxlen
        self.dropped: int = 0
        self._dict: dict[_KT, _VT] = {}
        self._lock: threading.Lock = threading.Lock()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({dict(self._dict)}, maxlen={self.maxlen})"

    def __getitem__(self, key: _KT) -> _VT:
        return self._dict[key]

    def __setitem__(self, key: _KT, value: _VT) -> None:
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

    def __delitem__(self, key: _KT) -> None:
        del self._dict[key]

    def __iter__(self) -> Iterator[_KT]:
        with self._lock:
            return iter(self._dict.copy())

    def __len__(self) -> int:
        return len(self._dict)

    @classmethod
    def from_map(
        cls: type["BoundedDict[_KT, _VT]"],
        maxlen: int | None,
        mapping: Mapping[_KT, _VT],
    ) -> "BoundedDict[_KT, _VT]":
        mapping = dict(mapping)
        bounded_dict = cls(maxlen)
        for key, value in mapping.items():
            bounded_dict[key] = value
        return bounded_dict
