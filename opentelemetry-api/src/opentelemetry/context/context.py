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
    """
    The Context interface provides a wrapper for the different
    mechanisms that are used to propagate context in Python.
    Implementations can be made available via entry_points and
    selected through environment variables.
    """

    @abstractmethod
    def set_value(self, key: str, value: "object") -> None:
        """
        Set a value in this context

        Args:
            key: The key for the value to set.
            value: The value to set.
        """

    @abstractmethod
    def get_value(self, key: str) -> "object":
        """
        Get a value from this context

        Args:
            key: The key for the value to retrieve.
        """

    @abstractmethod
    def remove_value(self, key: str) -> None:
        """
        Remove a value from this context

        Args:
            key: The key for the value to remove.
        """

    def copy(self) -> "Context":
        """Return a copy of this context"""

        return deepcopy(self)


__all__ = ["Context"]
