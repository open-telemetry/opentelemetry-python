# Copyright The OpenTelemetry Authors
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

import weakref
from os import register_at_fork
from threading import Lock
from typing import Callable


class Once:
    """Execute a function exactly once and block all callers until the function returns

    Same as golang's `sync.Once <https://pkg.go.dev/sync#Once>`_
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._done = False
        weak_reinit = weakref.WeakMethod(self._at_fork_reinit)
        register_at_fork(after_in_child=lambda: weak_reinit()())

    def _at_fork_reinit(self):
        self._lock._at_fork_reinit()

    def do_once(self, func: Callable[[], None]) -> bool:
        """Execute ``func`` if it hasn't been executed or return.

        Will block until ``func`` has been called by one thread.

        Returns:
            Whether or not ``func`` was executed in this call
        """

        # fast path, try to avoid locking
        if self._done:
            return False

        with self._lock:
            if not self._done:
                func()
                self._done = True
                return True
        return False
