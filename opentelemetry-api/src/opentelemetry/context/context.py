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


from abc import ABC, abstractmethod
from contextlib import contextmanager
from copy import deepcopy
from typing import Dict, Iterator


class Context(ABC):
    @abstractmethod
    def set_value(self, key: str, value: "object") -> None:
        """Set a value in this context"""

    @abstractmethod
    def get_value(self, key: str) -> "object":
        """Get a value from this context"""

    @abstractmethod
    def remove_value(self, key: str) -> None:
        """Remove a value from this context"""

    @contextmanager
    def use(self, **kwargs: Dict[str, object]) -> Iterator[None]:
        snapshot = {key: self.get_value(key) for key in kwargs}
        for key in kwargs:
            self.set_value(key, kwargs[key])
        yield
        for key in kwargs:
            self.set_value(key, snapshot[key])

    def copy(self) -> "Context":
        """Return a copy of this context"""

        return deepcopy(self)


__all__ = ["Context"]
