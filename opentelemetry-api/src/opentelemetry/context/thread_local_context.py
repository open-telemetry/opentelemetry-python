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
import typing  # pylint: disable=unused-import

from . import base_context


class ThreadLocalRuntimeContext(base_context.BaseContext):
    class Slot(base_context.BaseContext.Slot):
        _thread_local = threading.local()

        def __init__(self, name: str, default: "object"):
            # pylint: disable=super-init-not-called
            self.name = name
            self.default = base_context.wrap_callable(
                default
            )  # type: typing.Callable[..., object]

        def clear(self) -> None:
            setattr(self._thread_local, self.name, self.default())

        def get(self) -> "object":
            try:
                got = getattr(self._thread_local, self.name)  # type: object
                return got
            except AttributeError:
                value = self.default()
                self.set(value)
                return value

        def set(self, value: "object") -> None:
            setattr(self._thread_local, self.name, value)
