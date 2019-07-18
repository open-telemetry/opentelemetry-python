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


class BaseRuntimeContext:
    class Slot:
        def clear(self) -> None:
            raise NotImplementedError

        def get(self) -> typing.Any:
            raise NotImplementedError

        def set(self, value) -> None:
            raise NotImplementedError

    _lock = threading.Lock()
    _slots: typing.Dict[str, Slot] = {}

    @classmethod
    def clear(cls) -> None:
        """Clear all slots to their default value."""
        keys = cls._slots.keys()
        for name in keys:
            slot = cls._slots[name]
            slot.clear()

    @classmethod
    def register_slot(cls, name: str, default: typing.Any = None) -> None:
        """Register a context slot with an optional default value.

        :type name: str
        :param name: The name of the context slot.

        :type default: object
        :param name: The default value of the slot, can be a value or lambda.

        :returns: The registered slot.
        """
        with cls._lock:
            if name in cls._slots:
                raise ValueError('slot {} already registered'.format(name))
            slot = cls.Slot(name, default)
            cls._slots[name] = slot
            return slot

    def apply(self, snapshot) -> None:
        """Set the current context from a given snapshot dictionary"""

        for name in snapshot:
            setattr(self, name, snapshot[name])

    def snapshot(self) -> typing.Dict[str, typing.Any]:
        """Return a dictionary of current slots by reference."""

        keys = self._slots.keys()
        return dict((n, self._slots[n].get()) for n in keys)

    def __repr__(self) -> str:
        return '{}({})'.format(type(self).__name__, self.snapshot())

    def __getattr__(self, name) -> typing.Any:
        if name not in self._slots:
            self.register_slot(name, None)
        slot = self._slots[name]
        return slot.get()

    def __setattr__(self, name, value) -> None:
        if name not in self._slots:
            self.register_slot(name, None)
        slot = self._slots[name]
        slot.set(value)

    def with_current_context(self, func) -> typing.Callable:
        """Capture the current context and apply it to the provided func"""

        caller_context = self.snapshot()

        def call_with_current_context(*args, **kwargs) -> typing.Any:
            try:
                backup_context = self.snapshot()
                self.apply(caller_context)
                return func(*args, **kwargs)
            finally:
                self.apply(backup_context)

        return call_with_current_context
