# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pyright: reportUnnecessaryIsInstance=false

"""Validation and size-limiting of telemetry attributes.

The OpenTelemetry specification restricts which Python values may be used as
an attribute value, and lets an SDK cap both the number of attributes and the
length of each string. This module holds the two pieces that enforce those
rules: ``_clean_attribute_value``, which coerces or drops an invalid
value, and :class:`BoundedAttributes`, the mapping that spans, log records and
metric measurements store their attributes in.

A value that cannot be represented is coerced to :class:`str` when the object
defines ``__str__`` or ``__repr__``, and is replaced with ``None`` otherwise.
The pair stays in the mapping either way and ``dropped`` is not incremented. A
key is treated differently: a key of a nested mapping that cannot be converted
is dropped along with its value. A warning is logged in every case. Note that
coercion calls ``__str__`` on the object, so a ``__str__`` that raises does
propagate to the caller.
"""

import copy
import logging
import threading
from collections.abc import Mapping, MutableMapping, Sequence
from types import NoneType
from typing import TYPE_CHECKING, Any, overload

from typing_extensions import assert_never, deprecated

from opentelemetry.util import types

_logger = logging.getLogger(__name__)


# Calling str(x) will use an object's `__str__` method if it exists, otherwise it will use it's `__repr__` method.
# If neither is defined it uses the base class's `object.__repr__` method, which returns a string that is hard to understand.
# So in that case we drop the key/value pair.
def _is_non_custom_str(key: Any) -> bool:
    """Report whether converting ``key`` to a string would produce something useful.

    Args:
        key: The object about to be converted with :func:`str`. It is an
            attribute key or an attribute value.

    Returns:
        ``True`` when the type of ``key`` overrides ``__str__`` or
        ``__repr__``, so :func:`str` yields a meaningful result. ``False`` when
        neither is overridden, in which case :func:`str` would return the
        default ``<module.Class object at 0x...>`` form and the caller should
        drop the object instead.
    """
    return type(key).__str__ is not object.__str__ or type(key).__repr__ is not object.__repr__


@overload
def _clean_attribute_value(
    value: Mapping[str, types.AnyValue],
    max_string_value_length: int | None,
) -> Mapping[str, types.AnyValue]: ...


@overload
def _clean_attribute_value(
    value: types.AnyValue,
    max_string_value_length: int | None,
) -> types.AnyValue: ...


def _clean_attribute_value(
    value: types.AnyValue,
    max_string_value_length: int | None,
) -> types.AnyValue:
    """Recursively checks if an attribute value is valid and cleans it if required.

    String values are truncated to max_string_value_length if provided.
    Anything that isn't of `types.AnyValue`, we attempt to cast to `str`.
    If this fails, the value is replaced with None. Sequence's are converted to tuples and mappings
    are copied into new dicts.

    A mapping key that is empty, or that is not a string and cannot be
    converted to one, is dropped from the result and a warning is logged.

    Args:
        value: The attribute value to clean. Any Python object is accepted;
            one that is not a ``AnyValue`` is
            coerced or replaced rather than rejected.
        max_string_value_length: Maximum length of a string value, in
            characters. A longer string is truncated to this length and a
            warning is logged. Pass ``None`` to apply no limit.

    Returns:
        The recursively cleaned AnyValue.
    """
    if isinstance(value, (NoneType, bool, int, float, bytes)):
        return value
    if isinstance(value, str):
        if max_string_value_length is not None and len(value) > max_string_value_length:
            _logger.warning(
                "String attribute value exceeds max length of %d, truncating.",
                max_string_value_length,
            )
            value = value[:max_string_value_length]
        return value
    if isinstance(value, Sequence):
        return tuple(_clean_attribute_value(v, max_string_value_length) for v in value)
    if isinstance(value, Mapping):
        cleaned_mapping: dict[str, types.AnyValue] = {}
        for key, val in value.items():
            if not key:
                _logger.warning(
                    "invalid attribute key `%s`. must be non-empty string. Dropping key from attributes.",
                    key,
                )
                continue
            # Spec says to convert unknown types to strings if possible (here and below too).
            if not isinstance(key, str):
                _logger.warning(
                    "Invalid type `%s` for attribute key `%s`, must be a str. Key's `__str__/__repr__` method will be called if it exists, otherwise the key/value pair will be dropped.",
                    type(key),
                    key,
                )
                if _is_non_custom_str(key):
                    key = str(key)
                else:
                    continue
            cleaned_mapping[key] = _clean_attribute_value(val, max_string_value_length)
        return cleaned_mapping
    if TYPE_CHECKING:
        assert_never(value)
    _logger.warning(
        "Invalid type `%s` for attribute value. Expected one of bool, str, None, bytes, int, float or a "
        "Mapping or Sequence of those types. Value's __str__ method will be called if it exists, otherwise the value will be replaced with None.",
        type(value),
    )
    if _is_non_custom_str(value):
        return str(value)
    return None


class BoundedAttributes(MutableMapping[str, types.AnyValue]):
    """A dict with a fixed max capacity which cleans and potentially drops values to ensure they are valid attribute values.

    Args:
        maxlen: The maximum number of attributes to store, use None for no limit.
        attributes: The initial attributes to store.
        immutable: Defaults to true. Whether to allow adding/removing of attributes after the initialisation of the instance.
        max_value_len: The maximum length of string values, use None for no limit.
        extended_attributes: Deprecated. Kept for backwards compatibility. Extended attributes are now always used for attributes everywhere.

    When the dict is full, a new key is dropped; existing keys can still be updated. Attributes are made to be immutable when set in this container.
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
        """Build the mapping and store ``attributes`` in it.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.

        Raises:
            ValueError: If ``maxlen`` or ``max_value_len`` is negative.
        """
        if maxlen is not None and maxlen < 0:
            raise ValueError("maxlen must be valid int greater or equal to 0")
        if max_value_len is not None and max_value_len < 0:
            raise ValueError("max_value_len must be valid int greater or equal to 0")
        self._dict: dict[str, types.AnyValue] = {}
        self.maxlen = maxlen
        self.dropped = 0
        self.max_value_len = max_value_len
        self._lock = threading.Lock()
        # The spec allows the limit log to be emitted at most once per record, so track
        # it separately from ``dropped``, which also counts other kinds of drops.
        self._dropped_logged = False
        # setting False before adding items
        self._immutable = False
        if attributes:
            self._set_items(attributes)
        self._immutable = immutable

    def __repr__(self) -> str:
        """Render the stored attributes as a plain dict literal.

        Returns:
            The current attributes formatted as a :class:`dict` would be. The
            count of dropped attributes is not included.
        """
        return f"{dict(self._dict)}"

    def __getitem__(self, key: str) -> types.AnyValue:
        """Return the value stored under ``key``.

        Args:
            key: The attribute name to look up.

        Returns:
            The cleaned value stored under ``key``.

        Raises:
            KeyError: If ``key`` is absent, which includes the case where it
                was dropped for exceeding the capacity.
        """
        return self._dict[key]

    def _raise_if_immutable(self) -> None:
        """Reject a mutation when this instance was created immutable.

        Raises:
            TypeError: If this instance is immutable.
        """
        if self._immutable:
            raise TypeError("Cannot mutate immutable BoundedAttributes")

    def __setitem__(self, key: str, value: types.AnyValue) -> None:
        """Clean ``value`` and store it under ``key`` if there is capacity.

        An invalid key, or a key that does not fit within the capacity, is
        counted in ``dropped`` rather than stored, and no exception is raised.

        Args:
            key: The attribute name. It must be a non-empty :class:`str`.
            value: The attribute value, cleaned by
                ``_clean_attribute_value`` before being stored.

        Raises:
            TypeError: If this instance is immutable.
        """
        self._raise_if_immutable()
        if self.maxlen is not None and self.maxlen == 0:
            with self._lock:
                self.dropped += 1
                return
        if not key or not isinstance(key, str):
            _logger.warning(
                "invalid key `%s`. must be non-empty string. Dropping key from attributes.",
                key,
            )
            with self._lock:
                self.dropped += 1
            return
        cleaned = _clean_attribute_value(value, self.max_value_len)
        with self._lock:
            self._setitem_locked(key, cleaned)

    def _set_items(self, attributes: Mapping[str, types.AnyValue]) -> None:
        """Clean and store several attributes under a single lock acquisition.

        Args:
            attributes: The attributes to store. Each pair is cleaned by
                ``_clean_attribute_value``, and any pair dropped during
                cleaning is counted in ``dropped``.

        Raises:
            TypeError: If this instance is immutable.
        """
        self._raise_if_immutable()
        if self.maxlen is not None and self.maxlen == 0:
            with self._lock:
                self.dropped += len(attributes)
            return
        cleaned_attributes: Mapping[str, types.AnyValue] = _clean_attribute_value(attributes, self.max_value_len)
        with self._lock:
            self.dropped += len(attributes) - len(cleaned_attributes)
            for key, value in cleaned_attributes.items():
                self._setitem_locked(key, value)

    def _setitem_locked(self, key: str, value: types.AnyValue) -> None:
        """Store an already cleaned pair, assuming the lock is held.

        Re-setting a key that is already present moves it to the end and never
        counts against the capacity. Adding a new key once the mapping is full
        increments ``dropped`` and stores nothing. The full-mapping warning is
        logged at most once per instance.

        Args:
            key: The attribute name, already validated as a non-empty
                :class:`str`.
            value: The attribute value, already cleaned.
        """
        if key in self._dict:
            del self._dict[key]
        elif self.maxlen is not None and len(self._dict) >= self.maxlen:
            if not self._dropped_logged:
                self._dropped_logged = True
                _logger.warning(
                    "Attributes dict is full. Dropping new key-value pairs.",
                )
            self.dropped += 1
            return

        self._dict[key] = value

    def __delitem__(self, key: str) -> None:
        """Remove the attribute stored under ``key``.

        Args:
            key: The attribute name to remove.

        Raises:
            TypeError: If this instance is immutable.
            KeyError: If ``key`` is absent.
        """
        self._raise_if_immutable()
        del self._dict[key]

    def __iter__(self):
        """Iterate over the attribute names.

        A mutable instance is iterated over a snapshot of the names taken
        under the lock, so adding an attribute from another thread during
        iteration does not disturb it.

        Returns:
            An iterator over the attribute names, in insertion order.
        """
        if self._immutable:
            return iter(self._dict)
        with self._lock:
            return iter(list(self._dict))

    def __len__(self) -> int:
        """Return how many attributes are stored.

        Returns:
            The number of attributes currently held. Dropped attributes are
            not counted; read ``dropped`` for those.
        """
        return len(self._dict)

    def __deepcopy__(self, memo: dict[int, Any]) -> "BoundedAttributes":
        """Return a deep copy carrying the same limits and dropped count.

        The stored values are copied directly rather than re-cleaned, since
        they were cleaned when they were first stored.

        Args:
            memo: The memo dict :func:`copy.deepcopy` uses to track objects it
                has already copied.

        Returns:
            A new instance holding deep copies of the values, with the same
            ``maxlen``, ``max_value_len``, immutability and ``dropped`` count.
        """
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

    def copy(self) -> MutableMapping[str, types.AnyValue]:
        """Return the stored attributes as an ordinary mutable mapping.

        The result is a shallow copy and carries no capacity limit, so writing
        to it neither affects this instance nor drops anything.

        Returns:
            A plain :class:`dict` holding the current attributes.
        """
        return self._dict.copy()
