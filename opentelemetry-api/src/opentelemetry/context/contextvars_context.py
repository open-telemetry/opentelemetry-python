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
from contextvars import ContextVar
from copy import copy
from sys import version_info

from opentelemetry.context.context import Context

if (3, 5, 3) <= version_info < (3, 7):
    import aiocontextvars  # pylint:disable=unused-import

elif (3, 4) < version_info <= (3, 5, 2):
    import opentelemetry.context.aiocontextvarsfix  # pylint:disable=unused-import


class ContextVarsContext(Context):
    def __init__(self) -> None:
        self._contextvars = {}  # type: typing.Dict[str, ContextVar[object]]

    def set_value(self, key: str, value: "object") -> None:
        """Set a value in this context"""
        if key not in self._contextvars.keys():
            self._contextvars[key] = ContextVar(key)

        self._contextvars[key].set(value)

    def get_value(self, key: str) -> "object":
        """Get a value from this context"""
        if key in self._contextvars:
            try:
                return self._contextvars[key].get()
            except LookupError:
                pass
        return None

    def remove_value(self, key: str) -> None:
        """Remove a value from this context"""
        if key in self._contextvars.keys():
            self._contextvars.pop(key)

    def copy(self) -> Context:
        """Return a copy of this context"""

        context_copy = ContextVarsContext()

        for key, value in self._contextvars.items():
            context_copy.set_value(key, copy(value))

        return context_copy


__all__ = ["ContextVarsContext"]
