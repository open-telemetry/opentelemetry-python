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
from copy import copy

from opentelemetry.context.context import RuntimeContext


class DefaultRuntimeContext(RuntimeContext):
    """A default implementation of the RuntimeContext interface using
    a dictionary to store values.
    """

    def __init__(self) -> None:
        self._values = {}  # type: typing.Dict[str, object]

    def set_value(self, key: str, value: "object") -> None:
        """See `opentelemetry.context.RuntimeContext.set_value`."""
        self._values[key] = value

    def get_value(self, key: str) -> "object":
        """See `opentelemetry.context.RuntimeContext.get_value`."""
        return self._values.get(key)

    def remove_value(self, key: str) -> None:
        """See `opentelemetry.context.RuntimeContext.remove_value`."""
        self._values.pop(key, None)

    def copy(self) -> "RuntimeContext":
        """See `opentelemetry.context.RuntimeContext.copy`."""
        context_copy = DefaultRuntimeContext()
        for key, value in self._values.items():
            context_copy.set_value(key, copy(value))
        return context_copy

    def snapshot(self) -> typing.Dict[str, "object"]:
        """See `opentelemetry.context.RuntimeContext.snapshot`."""
        return dict((key, value) for key, value in self._values.items())

    def apply(self, snapshot: typing.Dict[str, "object"]) -> None:
        """See `opentelemetry.context.RuntimeContext.apply`."""
        for name in snapshot:
            self.set_value(name, snapshot[name])


__all__ = ["DefaultRuntimeContext"]
