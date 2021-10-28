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
This is the API.

This module includes all functions and classes with their respective methods
that an SDK must implement. SDKs must implement the contents of this module
exactly, with the same names and signatures for functions and methods. This is
necessary because the API proxy objects will call the SDK functions and methods
in the exact same way as they are defined here.
"""

from abc import ABC, abstractmethod


# There is no way to mandate the implementation of a function in a Python
# module, so this is added to inform SDK implementations that this function is
# to be implemented. A mechanism that checks SDK compliance can be implemented
# as well and it can use the contents of this module to check SDKs.
def function(a: int, b: int) -> float:
    pass


class Class0(ABC):

    @abstractmethod
    def __init__(self, a: int) -> None:
        pass

    @abstractmethod
    def method(self, a: int, b: int) -> float:
        pass
