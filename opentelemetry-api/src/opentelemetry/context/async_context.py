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

try:
    from contextvars import ContextVar
except ImportError:
    pass
else:
    # import contextvars
    import typing
    from . import base_context

    class ContextVarSlot(base_context.Slot):
        def __init__(self, name: str, default: object):
            # pylint: disable=super-init-not-called
            self.name = name
            self.contextvar = ContextVar(name)  # type: ContextVar[object]
            self.default = base_context.wrap_callable(
                default
            )  # type: typing.Callable[..., object]

        def clear(self) -> None:
            self.contextvar.set(self.default())

        def get(self) -> object:
            try:
                return self.contextvar.get()
            except LookupError:
                value = self.default()
                self.set(value)
                return value

        def set(self, value: object) -> None:
            self.contextvar.set(value)

    class AsyncRuntimeContext(base_context.Context):
        def with_current_context(
            self, func: typing.Callable[..., "object"]
        ) -> typing.Callable[..., "object"]:
            """Capture the current context and apply it to the provided func.
            """

            # TODO: implement this
            # ctx = contextvars.copy_context()
            # ctx.run()
            # caller_context = self.current()

            # def call_with_current_context(
            #     *args: "object", **kwargs: "object"
            # ) -> "object":
            #     try:
            #         backup_context = self.current()
            #         self.set_current(caller_context)
            #         # return ctx.run(func(*args, **kwargs))
            #         return func(*args, **kwargs)
            #     finally:
            #         self.set_current(backup_context)

            # return call_with_current_context
