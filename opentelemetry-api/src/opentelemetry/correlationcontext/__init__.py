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
from typing import Optional

from opentelemetry.context import Context, current
from opentelemetry.propagation import Extractor, Injector

PRINTABLE = frozenset(
    itertools.chain(
        string.ascii_letters, string.digits, string.punctuation, " "
    )
)


# TODO: are Entry* classes still needed here?
class EntryMetadata:
    """A class representing metadata of a CorrelationContext entry

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
    """A class representing a key for a CorrelationContext entry"""

    def __new__(cls, value: str) -> "EntryKey":
        return cls.create(value)

    @staticmethod
    def create(value: str) -> "EntryKey":
        # pylint: disable=len-as-condition
        if not 0 < len(value) <= 255 or any(c not in PRINTABLE for c in value):
            raise ValueError("Invalid EntryKey", value)

        return typing.cast(EntryKey, value)


class EntryValue(str):
    """A class representing the value of a CorrelationContext entry"""

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


# TODO: is CorrelationContext still needed here?
class CorrelationContext:
    """A container for distributed context entries"""


class CorrelationContextManager:
    @classmethod
    def set_correlation(
        cls, key: str, value: "object", context: Optional[Context] = None
    ) -> Context:
        return current().set_value(key, value, context=context)

    @classmethod
    def correlation(
        cls, key: str, context: Optional[Context] = None
    ) -> "object":
        return current().value(key, context=context)

    @classmethod
    def remove_correlation(cls, context: Optional[Context] = None) -> Context:
        pass

    @classmethod
    def clear_correlation(cls, context: Optional[Context] = None) -> Context:
        pass
