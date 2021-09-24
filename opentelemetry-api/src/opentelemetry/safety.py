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
# type: ignore

from abc import ABC, abstractmethod
from functools import wraps
from warnings import warn


class BaseSafety(ABC):
    def __new__(cls, *args, _allow_instantiation=False, **kwargs):

        instance = object.__new__(cls)
        if _allow_instantiation:
            instance._init(*args, **kwargs)

        else:
            warn(f"{cls.__name__} should not be instantiated directly")
            instance = instance._get_no_op_class()()

        return instance

    @abstractmethod
    def _init(self, *args, **kwargs):
        pass

    @abstractmethod
    def _get_no_op_class(self):
        pass


def safety(no_op_return):
    def internal(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except Exception as error:  # pylint: disable=broad-except
                warn(error)

                return no_op_return

        return wrapper

    return internal
