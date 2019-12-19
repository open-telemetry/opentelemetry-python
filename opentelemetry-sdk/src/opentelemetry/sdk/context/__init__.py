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

import copy
import types
import typing

from .base_context import BaseRuntimeContext

__all__ = ["BaseRuntimeContext", "Context"]

try:
    from .async_context import AsyncRuntimeContext

    _CONTEXT = AsyncRuntimeContext()  # type: BaseRuntimeContext
except ImportError:
    from .thread_local_context import ThreadLocalRuntimeContext

    _CONTEXT = ThreadLocalRuntimeContext()


class Context:
    def __init__(self):
        self.contents = {}
        self.slot_name = "{}".format(id(self))
        self._slot = _CONTEXT.register_slot(self.slot_name)
        self._slot.set(self)

    def __enter__(self) -> "Context":
        return self

    def __exit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]],
        exc_val: typing.Optional[BaseException],
        exc_tb: typing.Optional[types.TracebackType],
    ) -> None:
        pass

    def get(self, key: str) -> "object":
        return self.contents.get(key)

    @classmethod
    def value(
        cls, key: str, context: typing.Optional["Context"] = None
    ) -> "object":
        if context is None:
            return cls.current().contents.get(key)
        return context.contents.get(key)

    @classmethod
    def set_value(cls, key: str, value: "object") -> "Context":
        cls.current().contents[key] = value
        return cls.snapshot()

    @classmethod
    def current(cls) -> "Context":
        if _CONTEXT.current_context is None:
            ctx = Context()
            cls.set_current(ctx)
        return getattr(_CONTEXT, _CONTEXT.current_context.get())

    @classmethod
    def snapshot(cls) -> "Context":
        snapshot = Context()
        snapshot.contents = cls.current().contents.copy()
        return snapshot

    @classmethod
    def set_current(cls, context: "Context"):
        if _CONTEXT.current_context is None:
            _CONTEXT.current_context = _CONTEXT.register_slot(
                # change the key here
                "__current_prop_context__"
            )
        _CONTEXT.current_context.set(context.slot_name)

    @classmethod
    def use(cls, **kwargs: typing.Dict[str, object]) -> typing.Iterator[None]:
        return _CONTEXT.use(**kwargs)

    @classmethod
    def register_slot(
        cls, name: str, default: "object" = None
    ) -> "BaseRuntimeContext.Slot":
        return _CONTEXT.register_slot(name, default)
