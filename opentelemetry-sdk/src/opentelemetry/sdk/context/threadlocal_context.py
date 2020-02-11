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

import threading
import typing

from opentelemetry.context import Context, RuntimeContext

_CONTEXT_KEY = "current_context"


class ThreadLocalRuntimeContext(RuntimeContext):
    """An implementation of the RuntimeContext interface
    which uses thread-local storage under the hood. This
    implementation is available for usage with Python 3.4.
    """

    def __init__(self) -> None:
        self._thread_local = threading.local()
        self._current_context = threading.local()

    def set_value(self, key: str, value: "object") -> None:
        """See `opentelemetry.context.RuntimeContext.set_value`."""
        setattr(self._thread_local, key, value)

    def get_value(self, key: str) -> "object":
        """See `opentelemetry.context.RuntimeContext.get_value`."""
        try:
            got = getattr(self._thread_local, key)  # type: object
            return got
        except AttributeError:
            return None

    def remove_value(self, key: str) -> None:
        """See `opentelemetry.context.RuntimeContext.remove_value`."""
        try:
            delattr(self._thread_local, key)
        except AttributeError:
            pass

    def set_current(self, context: Context) -> None:
        """See `opentelemetry.context.RuntimeContext.set_current`."""
        setattr(self._current_context, _CONTEXT_KEY, context)

    def get_current(self) -> Context:
        """See `opentelemetry.context.RuntimeContext.get_current`."""
        try:
            got = getattr(self._current_context, _CONTEXT_KEY)  # type: object
        except AttributeError:
            values = dict(
                (key, value)
                for key, value in self._thread_local.__dict__.items()
            )
            setattr(
                self._current_context, _CONTEXT_KEY, Context(values),
            )
            got = getattr(self._current_context, _CONTEXT_KEY)
        return got


__all__ = ["ThreadLocalRuntimeContext"]
