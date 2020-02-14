# Copyright 2020, OpenTelemetry Authors
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

import threading

from opentelemetry.context.context import Context, RuntimeContext


class ThreadLocalRuntimeContext(RuntimeContext):
    """An implementation of the RuntimeContext interface
    which uses thread-local storage under the hood. This
    implementation is available for usage with Python 3.4.
    """

    _CONTEXT_KEY = "current_context"

    def __init__(self) -> None:
        self._current_context = threading.local()

    def set_current(self, context: Context) -> object:
        """See `opentelemetry.context.RuntimeContext.set_current`."""
        current = self.get_current()
        setattr(self._current_context, str(id(current)), current)
        setattr(self._current_context, self._CONTEXT_KEY, context)
        return str(id(current))

    def get_current(self) -> Context:
        """See `opentelemetry.context.RuntimeContext.get_current`."""
        if not hasattr(self._current_context, self._CONTEXT_KEY):
            setattr(
                self._current_context, self._CONTEXT_KEY, Context(),
            )
        context = getattr(
            self._current_context, self._CONTEXT_KEY
        )  # type: Context
        return context

    def reset(self, token: object) -> None:
        """See `opentelemetry.context.RuntimeContext.reset`."""
        if not hasattr(self._current_context, str(token)):
            raise ValueError("invalid token")
        context = getattr(self._current_context, str(token))  # type: Context
        setattr(self._current_context, self._CONTEXT_KEY, context)


__all__ = ["ThreadLocalRuntimeContext"]
