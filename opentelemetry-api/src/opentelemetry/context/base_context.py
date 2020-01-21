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

import abc
import threading
import typing
from contextlib import contextmanager


def wrap_callable(target: "object") -> typing.Callable[[], object]:
    if callable(target):
        return target
    return lambda: target


class Context(abc.ABC):
    def __init__(self) -> None:
        self.snapshot = {}

    def get(self, key: str) -> typing.Optional["object"]:
        return self.snapshot.get(key)

    @contextmanager
    def use(self, **kwargs: typing.Dict[str, object]) -> typing.Iterator[None]:
        snapshot = self.current()
        for key in kwargs:
            self.set_value(key, kwargs[key])
        yield
        self.set_current(snapshot)

    def with_current_context(
        self, func: typing.Callable[..., "object"]
    ) -> typing.Callable[..., "object"]:
        """Capture the current context and apply it to the provided func.
        """

        caller_context = self.current()

        def call_with_current_context(
            *args: "object", **kwargs: "object"
        ) -> "object":
            try:
                backup_context = self.current()
                self.set_current(caller_context)
                return func(*args, **kwargs)
            finally:
                self.set_current(backup_context)

        return call_with_current_context

    @abc.abstractmethod
    def current(self) -> "Context":
        """
        To access the context associated with program execution,
        the Context API provides a function which takes no arguments
        and returns a Context.
        """

    @abc.abstractmethod
    def set_current(self, context: "Context") -> None:
        """
        To associate a context with program execution, the Context
        API provides a function which takes a Context.
        """

    @abc.abstractmethod
    def set_value(
        self,
        key: str,
        value: "object",
        context: typing.Optional["Context"] = None,
    ) -> "Context":
        """
        To record the local state of a cross-cutting concern, the
        Context API provides a function which takes a context, a
        key, and a value as input, and returns an updated context
        which contains the new value.

        Args:
            key:
            value:
        """

    @abc.abstractmethod
    def value(
        self, key: str, context: typing.Optional["Context"] = None
    ) -> typing.Optional["object"]:
        """
        To access the local state of an concern, the Context API
        provides a function which takes a context and a key as input,
        and returns a value.
        """


class BaseContext(Context):
    class Slot:
        def __init__(self, name: str, default: "object"):
            raise NotImplementedError

        def clear(self) -> None:
            raise NotImplementedError

        def get(self) -> "object":
            raise NotImplementedError

        def set(self, value: "object") -> None:
            raise NotImplementedError

    _lock = threading.Lock()
    _slots = {}  # type: typing.Dict[str, 'BaseContext.Slot']

    @classmethod
    def clear(cls) -> None:
        """Clear all slots to their default value."""
        keys = cls._slots.keys()
        for name in keys:
            slot = cls._slots[name]
            slot.clear()

    @classmethod
    def register_slot(
        cls, name: str, default: "object" = None
    ) -> "BaseContext.Slot":
        """Register a context slot with an optional default value.

        :type name: str
        :param name: The name of the context slot.

        :type default: object
        :param name: The default value of the slot, can be a value or lambda.

        :returns: The registered slot.
        """
        with cls._lock:
            if name not in cls._slots:
                cls._slots[name] = cls.Slot(name, default)
            return cls._slots[name]

    def merge(self, context: Context) -> Context:
        new_context = self.current()
        for key in context.snapshot:
            new_context.snapshot[key] = context.snapshot[key]
        return new_context

    def _freeze(self) -> typing.Dict[str, "object"]:
        """Return a dictionary of current slots by reference."""

        keys = self._slots.keys()
        return dict((n, self._slots[n].get()) for n in keys)

    def __repr__(self) -> str:
        return "{}({})".format(type(self).__name__, self._freeze())

    def _set(self, key: str, value: "object") -> None:
        """
        Set creates a Slot for the value if none exists, and sets the
        value for that slot.

        Args:
            key: Name of the value
            value: Contents of the value
        """
        if key not in self._slots:
            self.register_slot(key, None)
        slot = self._slots[key]
        slot.set(value)

    def value(
        self, key: str, context: typing.Optional["Context"] = None
    ) -> typing.Optional["object"]:
        """
        To access the local state of an concern, the Context API
        provides a function which takes a context and a key as input,
        and returns a value.

        Args:
            key: Name of the value
            context:
        """
        if context:
            return context.get(key)

        return self.current().get(key)

    def set_value(
        self,
        key: str,
        value: "object",
        context: typing.Optional["Context"] = None,
    ) -> "Context":
        """
        To record the local state of a cross-cutting concern, the
        Context API provides a function which takes a context, a
        key, and a value as input, and returns an updated context
        which contains the new value.

        Args:
            key: Name of the value
            value: Contents of the value
            context:
        """
        if context:
            new_context = self.__class__()
            for name in context.snapshot:
                new_context.snapshot[name] = context.snapshot[name]
            new_context.snapshot[key] = value
            return new_context
        self._set(key, value)
        return self.current()

    def current(self) -> "Context":
        """
        To access the context associated with program execution,
        the Context API provides a function which takes no arguments
        and returns a Context.
        """
        ctx = self.__class__()
        ctx.snapshot = self._freeze()
        return ctx

    def set_current(self, context: "Context") -> None:
        """
        To associate a context with program execution, the Context
        API provides a function which takes a Context.
        """
        keys = self._slots.keys()
        for name in keys:
            slot = self._slots[name]
            slot.clear()
        self._slots.clear()
        if context.snapshot:
            for name in context.snapshot:
                self._set(name, context.snapshot[name])
