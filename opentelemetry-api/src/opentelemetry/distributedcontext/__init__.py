# Copyright 2019, OpenTelemetry Authors
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

import itertools
import string
import typing
from contextlib import contextmanager

from opentelemetry.context import get_value, set_current, set_value
from opentelemetry.context.context import Context

PRINTABLE = frozenset(
    itertools.chain(
        string.ascii_letters, string.digits, string.punctuation, " "
    )
)


class EntryMetadata:
    """A class representing metadata of a DistributedContext entry

    Args:
        entry_ttl: The time to live (in service hops) of an entry. Must be
                   initially set to either :attr:`EntryMetadata.NO_PROPAGATION`
                   or :attr:`EntryMetadata.UNLIMITED_PROPAGATION`.
    """

    NO_PROPAGATION = 0
    UNLIMITED_PROPAGATION = -1

    def __init__(self, entry_ttl: int) -> None:
        self.entry_ttl = entry_ttl


class EntryKey(str):
    """A class representing a key for a DistributedContext entry"""

    def __new__(cls, value: str) -> "EntryKey":
        return cls.create(value)

    @staticmethod
    def create(value: str) -> "EntryKey":
        # pylint: disable=len-as-condition
        if not 0 < len(value) <= 255 or any(c not in PRINTABLE for c in value):
            raise ValueError("Invalid EntryKey", value)

        return typing.cast(EntryKey, value)


class EntryValue(str):
    """A class representing the value of a DistributedContext entry"""

    def __new__(cls, value: str) -> "EntryValue":
        return cls.create(value)

    @staticmethod
    def create(value: str) -> "EntryValue":
        if any(c not in PRINTABLE for c in value):
            raise ValueError("Invalid EntryValue", value)

        return typing.cast(EntryValue, value)


class Entry:
    def __init__(
        self, metadata: EntryMetadata, key: EntryKey, value: EntryValue
    ) -> None:
        self.metadata = metadata
        self.key = key
        self.value = value


class DistributedContext:
    """A container for distributed context entries"""

    def __init__(self, entries: typing.Iterable[Entry]) -> None:
        self._container = {entry.key: entry for entry in entries}

    def get_entries(self) -> typing.Iterable[Entry]:
        """Returns an immutable iterator to entries."""
        return self._container.values()

    def get_entry_value(self, key: EntryKey) -> typing.Optional[EntryValue]:
        """Returns the entry associated with a key or None

        Args:
            key: the key with which to perform a lookup
        """
        if key in self._container:
            return self._container[key].value
        return None


class DistributedContextManager:
    def get_current_context(
        self, context: typing.Optional[Context] = None
    ) -> typing.Optional[DistributedContext]:
        """Gets the current DistributedContext.

        Returns:
            A DistributedContext instance representing the current context.
        """

    @contextmanager  # type: ignore
    def use_context(
        self, context: DistributedContext
    ) -> typing.Iterator[DistributedContext]:
        """Context manager for controlling a DistributedContext lifetime.

        Set the context as the active DistributedContext.

        On exiting, the context manager will restore the parent
        DistributedContext.

        Args:
            context: A DistributedContext instance to make current.
        """
        # pylint: disable=no-self-use
        yield context


_DISTRIBUTED_CONTEXT_KEY = "DistributedContext"


def distributed_context_from_context(
    context: typing.Optional[Context] = None,
) -> DistributedContext:
    return get_value(_DISTRIBUTED_CONTEXT_KEY, context)  # type: ignore


def with_distributed_context(
    dctx: DistributedContext, context: typing.Optional[Context] = None
) -> None:
    set_current(set_value(_DISTRIBUTED_CONTEXT_KEY, dctx, context=context))
