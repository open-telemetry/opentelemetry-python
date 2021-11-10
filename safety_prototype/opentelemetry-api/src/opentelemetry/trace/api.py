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
from contextlib import contextmanager

from opentelemetry.configuration import _get_sdk_module


# There is no way to mandate the implementation of a function in a Python
# module, so this is added to inform SDK implementations that this function is
# to be implemented. A mechanism that checks SDK compliance can be implemented
# as well and it can use the contents of this module to check SDKs.
def function(a: int, b: int) -> float:
    pass


class _BaseAPI(ABC):

    def __init__(self, *args, **kwargs) -> None:
        self._sdk_instance = None
        self._init_args = args
        self._init_kwargs = kwargs

    def __getattribute__(self, name):

        if object.__getattribute__(self, "_sdk_instance") is None:
            self._sdk_instance = (
                getattr(
                    _get_sdk_module("trace"),
                    object.__getattribute__(self, "__class__").__name__
                )
                (
                    *object.__getattribute__(self, "_init_args"),
                    **object.__getattribute__(self, "_init_kwargs"),
                )
            )

        return object.__getattribute__(self, name)


class Class0(_BaseAPI):

    def __init__(self, a: int) -> None:
        super().__init__(a)

    @abstractmethod
    def method_0(self, a: int, b: int) -> float:
        pass


class Class1(_BaseAPI):

    @contextmanager
    @abstractmethod
    def method_0(self, a: int) -> Class0:
        pass
