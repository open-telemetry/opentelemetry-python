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
This an implementation of the API where every function or method is safe.

Any call to a function or method defined here passes its arguments to a
corresponding underlying SDK function or method. In this way, objects defined
in this module act as proxies and (with the SDK setting function) are the only
objects the user has contact with.
"""
from contextlib import contextmanager

from opentelemetry._safety import _safe_function
from opentelemetry.trace.api import Class0, Class1
from opentelemetry.configuration import _get_sdk_module


@_safe_function(0.0)
def function(a: int, b: int) -> float:
    return _get_sdk_module("trace").function(a, b)


class Class0(Class0):

    @_safe_function(0.0)
    def method_0(self, a: int, b: int) -> float:
        return self._sdk_instance.method_0(a, b)


class Class1(Class1):

    @contextmanager
    @_safe_function(Class0(0))
    def method_0(self, a: int) -> Class0:
        return self._sdk_instance.method_0(a)
