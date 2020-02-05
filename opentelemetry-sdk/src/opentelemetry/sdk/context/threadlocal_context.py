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

from opentelemetry.context import Context


class ThreadLocalContext(Context):
    """
    An implementation of the Context interface
    which uses thread-local storage under the hood. This
    implementation is available for usage with Python 3.4.
    """

    def __init__(self) -> None:
        self._thread_local = threading.local()

    def set_value(self, key: str, value: "object") -> None:
        """Set a value in this context"""
        setattr(self._thread_local, key, value)

    def get_value(self, key: str) -> "object":
        """Get a value from this context"""
        try:
            got = getattr(self._thread_local, key)  # type: object
            return got
        except AttributeError:
            return None

    def remove_value(self, key: str) -> None:
        """Remove a value from this context"""
        delattr(self._thread_local, key)
