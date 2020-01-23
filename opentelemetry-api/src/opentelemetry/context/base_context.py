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

import abc
import typing


def wrap_callable(target: "object") -> typing.Callable[[], object]:
    if callable(target):
        return target
    return lambda: target


class Context:
    def __init__(self) -> None:
        self.snapshot = {}

    def value(self, name):
        return self.snapshot.get(name)


class Slot(abc.ABC):
    @abc.abstractmethod
    def __init__(self, name: str, default: "object"):
        raise NotImplementedError

    @abc.abstractmethod
    def clear(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self) -> "object":
        raise NotImplementedError

    @abc.abstractmethod
    def set(self, value: "object") -> None:
        raise NotImplementedError
