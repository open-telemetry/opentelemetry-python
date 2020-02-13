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

from opentelemetry import distributedcontext as dctx_api
from opentelemetry.context import Context, get_value, set_value
from opentelemetry.distributedcontext import (
    distributed_context_from_context,
    with_distributed_context,
)


class DistributedContextManager(dctx_api.DistributedContextManager):
    """See `opentelemetry.distributedcontext.DistributedContextManager`

    """

    def get_current_context(
        self, context: typing.Optional[Context] = None
    ) -> typing.Optional[dctx_api.DistributedContext]:
        """Gets the current DistributedContext.

        Returns:
            A DistributedContext instance representing the current context.
        """
        return distributed_context_from_context(context=context)

    @contextmanager
    def use_context(
        self, context: dctx_api.DistributedContext
    ) -> typing.Iterator[dctx_api.DistributedContext]:
        """Context manager for controlling a DistributedContext lifetime.

        Set the context as the active DistributedContext.

        On exiting, the context manager will restore the parent
        DistributedContext.

        Args:
            context: A DistributedContext instance to make current.
        """
        snapshot = distributed_context_from_context()
        with_distributed_context(context)

        try:
            yield context
        finally:
            with_distributed_context(snapshot)
