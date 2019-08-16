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
import contextvars
import typing

from opentelemetry import distributedcontext as dctx_api

_CURRENT_DISTRIBUTEDCONTEXT_CV = contextvars.ContextVar(
    'distributed_context',
    default=None,
)


class EntryMetadata(dctx_api.EntryMetadata):
    pass


class EntryKey(dctx_api.EntryKey):
    pass


class EntryValue(dctx_api.EntryValue):
    pass


class Entry(dctx_api.Entry):
    pass


class DistributedContext(dict, dctx_api.DistributedContext):
    def get_entries(self) -> typing.Iterable[Entry]:
        return self.values()

    def get_entry_value(self, key: EntryKey) -> typing.Optional[EntryValue]:
        return self.get(key)


class DistributedContextManager(dctx_api.DistributedContextManager):
    def __init__(self,
                 cv: 'contextvars.ContextVar' = _CURRENT_DISTRIBUTEDCONTEXT_CV,
                 ) -> None:
        self._cv = cv

    def get_current_context(self) -> typing.Optional[DistributedContext]:
        return self._cv.get(default=None)

    @contextmanager
    def use_context(
        self, context: DistributedContext
    ) -> typing.Iterator[DistributedContext]:
        token = self._cv.set(context)
        try:
            yield context
        finally:
            self._cv.reset(token)
