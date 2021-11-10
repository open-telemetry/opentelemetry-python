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

"""
This is the SDK.

Functions and methods are implemented here, their execution may cause
exceptions to be raised. SDK implementations may also raise exceptions
intentionally. Any exception raised in one of these functions or methods will
be caught by the safety mechanism in the API.
"""
from contextlib import contextmanager

from opentelemetry.trace.api import Class0, Class1


def function(a: int, b: int) -> float:
    return a / b


class Class0(Class0):

    def __init__(self, a: int) -> None:
        self._a = a
        super().__init__(a)

    def method_0(self, a: int, b: int) -> float:
        return self._a * (a / b)


class Class1(Class1):

    def method_0(self, a: int) -> 

    @contextmanager
    def method_1(self, a: int) -> Class0:
        print("before")
        yield Class0(a)
        print("after")
