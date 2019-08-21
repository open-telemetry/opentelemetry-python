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
import typing

from opentelemetry.context import Context
from opentelemetry import distributedcontext as dctx_api


class DistributedContext(dict, dctx_api.DistributedContext):
    """A container for distributed context entries"""

    def get_entries(self) -> typing.Iterable[dctx_api.Entry]:
        """Returns an immutable iterator to entries."""
        return self.values()

    def get_entry_value(
        self, key: dctx_api.EntryKey
    ) -> typing.Optional[dctx_api.EntryValue]:
        """Returns the entry associated with a key or None

        Args:
            key: the key with which to perform a lookup
        """
        return self.get(key)


class DistributedContextManager(dctx_api.DistributedContextManager):
    """See `opentelemetry.distributedcontext.DistributedContextManager`

    Args:
        name: The name of the context manager
    """

    def __init__(self, name: str = "") -> None:
        if name:
            slot_name = "DistributedContext.{}".format(name)
        else:
            slot_name = "DistributedContext"

        self._current_context = Context.register_slot(slot_name)

    def get_current_context(self) -> typing.Optional[DistributedContext]:
        """Gets the current DistributedContext.

        Returns:
            A DistributedContext instance representing the current context.
        """
        return self._current_context.get()

    @contextmanager
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
        snapshot = self._current_context.get()
        self._current_context.set(context)
        try:
            yield context
        finally:
            self._current_context.set(snapshot)
