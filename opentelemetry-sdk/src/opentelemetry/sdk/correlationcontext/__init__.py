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

import typing
from contextlib import contextmanager

from opentelemetry import correlationcontext as dctx_api
from opentelemetry.context import Context


class CorrelationContextManager(dctx_api.CorrelationContextManager):
    """See `opentelemetry.correlationcontext.CorrelationContextManager`

    Args:
        name: The name of the context manager
    """

    def __init__(self, name: str = "") -> None:
        if name:
            slot_name = "CorrelationContext.{}".format(name)
        else:
            slot_name = "CorrelationContext"

        self._current_context = Context.register_slot(slot_name)

    def current_context(self,) -> typing.Optional[dctx_api.CorrelationContext]:
        """Gets the current CorrelationContext.

        Returns:
            A CorrelationContext instance representing the current context.
        """
        return self._current_context.get()

    @contextmanager
    def use_context(
        self, context: dctx_api.CorrelationContext
    ) -> typing.Iterator[dctx_api.CorrelationContext]:
        """Context manager for controlling a CorrelationContext lifetime.

        Set the context as the active CorrelationContext.

        On exiting, the context manager will restore the parent
        CorrelationContext.

        Args:
            context: A CorrelationContext instance to make current.
        """
        snapshot = self._current_context.get()
        self._current_context.set(context)
        try:
            yield context
        finally:
            self._current_context.set(snapshot)
