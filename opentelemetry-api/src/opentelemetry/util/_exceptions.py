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

from typing import List


class _Failure(Exception):
    "Exception raised when a function fails"

    def __init__(self, method: str, exceptions: List[Exception]):
        super().__init__()
        self._method = method
        self._exceptions = exceptions

    def __str__(self) -> str:

        exceptions = ", ".join(
            [repr(exception) for exception in self._exceptions]
        )

        return (
            f"{self._method} failed with the following exceptions: "
            f"{exceptions}"
        )


class _Timeout(Exception):
    "Exception raised when a function times out"
