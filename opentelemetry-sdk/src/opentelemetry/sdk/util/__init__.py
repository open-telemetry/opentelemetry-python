# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Size-limited containers and small helpers shared across the SDK.

``BoundedList`` is the sequence a span stores its events and links in. It
keeps a fixed number of the most recent items and counts the rest in
``dropped`` rather than raising, so that instrumentation which records far
more than the configured limit degrades the telemetry and leaves the
application running.

``BoundedDict`` is the mapping equivalent and is deprecated. New code stores
attributes in ``opentelemetry.attributes.BoundedAttributes``, which also
validates and truncates the values.
"""

import copy
import datetime
import threading
from collections import deque
from collections.abc import MutableMapping, Sequence

from typing_extensions import deprecated


def ns_to_iso_str(nanoseconds):
    """Get an ISO 8601 string from time_ns value.

    The nanosecond count is divided by a float before being handed to
    ``datetime``, so the result keeps microsecond resolution at best and the
    last three digits of the input are lost.

    Args:
        nanoseconds: A timestamp as a count of nanoseconds since the Unix
            epoch, of the kind ``time.time_ns`` returns.

    Returns:
        The same instant in UTC, formatted as
        ``YYYY-MM-DDTHH:MM:SS.ffffffZ``.
    """
    ts = datetime.datetime.fromtimestamp(nanoseconds / 1e9, tz=datetime.timezone.utc)
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def get_dict_as_key(labels):
    """Converts a dict to be used as a unique key.

    Args:
        labels: The mapping to convert. A value that is a ``list`` is turned
            into a ``tuple`` so that it hashes; any other value is stored as
            it is and has to be hashable already.

    Returns:
        A ``tuple`` of key and value pairs, sorted by key, so that two
        mappings holding the same pairs produce equal keys whatever order
        they were built in.
    """
    return tuple(
        sorted(
            map(
                lambda kv: (kv[0], tuple(kv[1])) if isinstance(kv[1], list) else kv,
                labels.items(),
            )
        )
    )


class BoundedList(Sequence):
    """An append only list with a fixed max size.

    Calls to `append` and `extend` will drop the oldest elements if there is
    not enough room.

    The count of elements that were dropped is kept in the ``dropped``
    attribute, which a span exports as its dropped events or dropped links
    count. Reading and iterating are not themselves bounded: the sequence
    behaves like the ``deque`` it wraps.

    Args:
        maxlen: The number of elements to keep. Pass ``None`` to keep every
            element, in which case ``dropped`` stays at zero.
    """

    def __init__(self, maxlen: int | None):
        """Build an empty list.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self.dropped = 0
        self._dq = deque(maxlen=maxlen)  # type: deque
        self._lock = threading.Lock()

    def __deepcopy__(self, memo):
        """Copy the list and its elements, holding the lock while doing so.

        Args:
            memo: The mapping of already copied objects that
                ``copy.deepcopy`` threads through a copy operation. The new
                list is registered in it before its elements are copied, so
                that a cycle terminates.

        Returns:
            A new ``BoundedList`` holding deep copies of the elements, with
            the same ``dropped`` count and the same maximum length as this
            one, since the copied ``deque`` carries that length with it.
        """
        copy_ = BoundedList(0)
        memo[id(self)] = copy_
        with self._lock:
            copy_.dropped = self.dropped
            copy_._dq = copy.deepcopy(self._dq, memo)
        return copy_

    def __repr__(self):
        """Render the kept elements and the maximum length.

        Returns:
            A string of the form ``BoundedList([...], maxlen=...)``. The
            ``dropped`` count is not part of it.
        """
        return f"{type(self).__name__}({list(self._dq)}, maxlen={self._dq.maxlen})"

    def __getitem__(self, index):
        """Return the element at ``index`` among the kept ones.

        Args:
            index: A position or a slice, counted over the elements still
                held. A dropped element shifts every later position, so an
                index is not stable across an ``append`` that drops.

        Returns:
            The element, or the list of elements when ``index`` is a slice.

        Raises:
            IndexError: If ``index`` is out of range.
        """
        return self._dq[index]

    def __len__(self):
        """Return how many elements are still held.

        Returns:
            The number of kept elements, which never exceeds the maximum
            length. Dropped elements are not counted; ``dropped`` holds those.
        """
        return len(self._dq)

    def __iter__(self):
        """Iterate over a snapshot of the kept elements.

        The elements are copied into a list while the lock is held, so an
        append from another thread during iteration neither blocks nor
        changes what is yielded.

        Returns:
            An iterator over the elements held when the call was made.
        """
        with self._lock:
            return iter(list(self._dq))

    def append(self, item):
        """Add one element, dropping the oldest when the list is full.

        Args:
            item: The element to add. It is stored as it is, without
                validation or copying.
        """
        with self._lock:
            if self._dq.maxlen is not None and len(self._dq) == self._dq.maxlen:
                self.dropped += 1
            self._dq.append(item)

    def extend(self, seq):
        """Add several elements, dropping the oldest ones that no longer fit.

        Args:
            seq: The elements to add, in order. On a bounded list it has to
                support ``len``, so a one-shot iterator is accepted only when
                the list was built with ``maxlen=None``. When the whole
                sequence is longer than the maximum length, the earlier
                elements of ``seq`` itself are the ones dropped.
        """
        with self._lock:
            if self._dq.maxlen is not None:
                to_drop = len(seq) + len(self._dq) - self._dq.maxlen
                if to_drop > 0:
                    self.dropped += to_drop
            self._dq.extend(seq)

    @classmethod
    def from_seq(cls, maxlen, seq):
        """Build a bounded list already holding ``seq``.

        Args:
            maxlen: The number of elements to keep, or ``None`` to keep every
                element.
            seq: The initial elements, in order. Any iterable is accepted; it
                is materialised as a ``tuple`` first, so a generator works
                here even though ``extend`` alone would reject it on a
                bounded list.

        Returns:
            A new instance holding the last ``maxlen`` elements of ``seq``,
            with ``dropped`` set to the number that did not fit.
        """
        seq = tuple(seq)
        bounded_list = cls(maxlen)
        bounded_list.extend(seq)
        return bounded_list


@deprecated("Deprecated since version 1.4.0.")
class BoundedDict(MutableMapping):
    """An ordered dict with a fixed max capacity.

    Oldest elements are dropped when the dict is full and a new element is
    added.

    Deprecated since version 1.4.0. The SDK stores attributes in
    ``opentelemetry.attributes.BoundedAttributes`` instead, which validates
    and truncates values as well as bounding their number.

    Assigning to a key that is already present removes it and inserts it
    again, which moves it last. Eviction always takes the first key of that
    order, so the entry dropped is the one written longest ago, and rewriting
    a key protects it. Rewriting never drops anything itself.

    Args:
        maxlen: The number of entries to keep. Pass ``None`` to keep every
            entry. Pass 0 to drop every entry, counting each one in
            ``dropped``.
    """

    def __init__(self, maxlen: int | None):
        """Build an empty mapping.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.

        Raises:
            ValueError: If ``maxlen`` is not an ``int``, or is negative.
        """
        if maxlen is not None:
            if not isinstance(maxlen, int):
                raise ValueError
            if maxlen < 0:
                raise ValueError
        self.maxlen = maxlen
        self.dropped = 0
        self._dict = {}  # type: dict
        self._lock = threading.Lock()  # type: threading.Lock

    def __repr__(self):
        """Render the kept entries and the maximum length.

        Returns:
            A string of the form ``BoundedDict({...}, maxlen=...)``. The
            ``dropped`` count is not part of it.
        """
        return f"{type(self).__name__}({dict(self._dict)}, maxlen={self.maxlen})"

    def __getitem__(self, key):
        """Return the value stored under ``key``.

        Args:
            key: The key to look up.

        Returns:
            The stored value.

        Raises:
            KeyError: If ``key`` is absent, which includes the case where it
                was evicted to make room for a later key.
        """
        return self._dict[key]

    def __setitem__(self, key, value):
        """Store ``value`` under ``key``, evicting the oldest entry if needed.

        Nothing is raised when the mapping is full. The oldest entry is
        removed and ``dropped`` is incremented. When the maximum length is 0
        the new entry is counted in ``dropped`` and discarded at once.

        Args:
            key: The key to store under. It has to be hashable.
            value: The value to store. It is kept as it is, without
                validation.
        """
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
        """Remove the entry stored under ``key``.

        The lock is not taken, unlike for the other mutations, so a removal
        racing a write from another thread is not serialised.

        Args:
            key: The key to remove.

        Raises:
            KeyError: If ``key`` is absent.
        """
        del self._dict[key]

    def __iter__(self):
        """Iterate over a snapshot of the keys.

        Returns:
            An iterator over the keys held when the call was made, in
            insertion order. The snapshot is taken under the lock, so a write
            from another thread during iteration does not disturb it.
        """
        with self._lock:
            return iter(self._dict.copy())

    def __len__(self):
        """Return how many entries are still held.

        Returns:
            The number of kept entries, which never exceeds the maximum
            length. Dropped entries are not counted; ``dropped`` holds those.
        """
        return len(self._dict)

    @classmethod
    def from_map(cls, maxlen, mapping):
        """Build a bounded mapping already holding the entries of ``mapping``.

        Args:
            maxlen: The number of entries to keep, or ``None`` to keep every
                entry.
            mapping: The initial entries. They are inserted one at a time in
                iteration order, so when there are more of them than
                ``maxlen`` the earliest ones are evicted and counted in
                ``dropped``.

        Returns:
            A new instance holding the last ``maxlen`` entries of ``mapping``.

        Raises:
            ValueError: If ``maxlen`` is not an ``int``, or is negative.
        """
        mapping = dict(mapping)
        bounded_dict = cls(maxlen)
        for key, value in mapping.items():
            bounded_dict[key] = value
        return bounded_dict
