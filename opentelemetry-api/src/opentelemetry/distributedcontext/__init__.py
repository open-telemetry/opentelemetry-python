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

from contextlib import contextmanager
import string
import typing


class EntryMetadata:
    NO_PROPAGATION = 0
    UNLIMITED_PROPAGATION = -1

    def __init__(self, entry_ttl: int) -> None:
        self.entry_ttl = entry_ttl


class EntryKey(str):
    def __new__(cls, value):
        if len(value) > 255 or any(c not in string.printable for c in value):
            raise ValueError("Invalid EntryKey", value)
        return str.__new__(cls, value)


class EntryValue(str):
    def __new__(cls, value):
        if any(c not in string.printable for c in value):
            raise ValueError("Invalid EntryValue", value)
        return str.__new__(cls, value)


class Entry:
    def __init__(
        self, metadata: EntryMetadata, key: EntryKey, value: EntryValue
    ) -> None:
        self.metadata = metadata
        self.key = key
        self.value = value


class DistributedContext:
    def get_entries(self) -> typing.Iterable[Entry]:
        pass

    def get_entry_value(self, key: EntryKey) -> typing.Optional[EntryValue]:
        pass


class DistributedContextManager:
    def get_current_context(self) -> typing.Optional[DistributedContext]:
        pass

    @contextmanager
    def use_context(
        self, context: DistributedContext
    ) -> typing.Iterator[DistributedContext]:
        yield context
