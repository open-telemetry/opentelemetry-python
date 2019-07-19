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

from . import base_context


class ThreadLocalRuntimeContext(base_context.BaseRuntimeContext):
    class Slot(base_context.BaseRuntimeContext.Slot):
        _thread_local = threading.local()

        def __init__(self, name: str, default: 'object'):
            # pylint: disable=super-init-not-called
            self.name = name
            self.default: typing.Callable[..., object]
            self.default = base_context.wrap_callable(default)

        def clear(self) -> None:
            setattr(self._thread_local, self.name, self.default())

        def get(self) -> 'object':
            try:
                got: object = getattr(self._thread_local, self.name)
                return got
            except AttributeError:
                value = self.default()
                self.set(value)
                return value

        def set(self, value: 'object') -> None:
            setattr(self._thread_local, self.name, value)
