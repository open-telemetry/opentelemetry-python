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

from .base_context import BaseRuntimeContext

class ThreadLocalRuntimeContext(BaseRuntimeContext):
    class Slot(BaseRuntimeContext.Slot):
        _thread_local = threading.local()

        def __init__(self, name, default):
            self.name = name
            self.default = default if callable(default) else (lambda: default)

        def clear(self):
            setattr(self._thread_local, self.name, self.default())

        def get(self):
            try:
                return getattr(self._thread_local, self.name)
            except AttributeError:
                value = self.default()
                self.set(value)
                return value

        def set(self, value):
            setattr(self._thread_local, self.name, value)
