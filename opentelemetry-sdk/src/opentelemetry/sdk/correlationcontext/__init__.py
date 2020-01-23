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

from opentelemetry import correlationcontext as cctx_api
from opentelemetry.context import current, set_value, value


class CorrelationContextManager(cctx_api.CorrelationContextManager):
    """See `opentelemetry.correlationcontext.CorrelationContextManager`

    Args:
        name: The name of the context manager
    """

    def __init__(self, name: str = "") -> None:
        if name:
            self.slot_name = "CorrelationContext.{}".format(name)
        else:
            self.slot_name = "CorrelationContext"

    def current_context(self,) -> typing.Optional[cctx_api.CorrelationContext]:
        """Gets the current CorrelationContext.

        Returns:
            A CorrelationContext instance representing the current context.
        """
        return value(self.slot_name)

    @contextmanager
    def use_context(
        self, context: cctx_api.CorrelationContext
    ) -> typing.Iterator[cctx_api.CorrelationContext]:
        """Context manager for controlling a CorrelationContext lifetime.

        Set the context as the active CorrelationContext.

        On exiting, the context manager will restore the parent
        CorrelationContext.

        Args:
            context: A CorrelationContext instance to make current.
        """
        snapshot = current().value(self.slot_name)
        set_value(self.slot_name, context)
        try:
            yield context
        finally:
            set_value(self.slot_name, snapshot)
