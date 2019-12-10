# Copyright 2020, OpenTelemetry Authors
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

"""
OpenTelemetry Auto Instrumentation Patcher
"""

from abc import ABC, abstractmethod
from logging import getLogger

_LOG = getLogger(__name__)


class BasePatcher(ABC):
    """An ABC for patchers"""

    def __init__(self):
        self._is_patched = False

    @abstractmethod
    def _patch(self) -> None:
        """Patch"""

    @abstractmethod
    def _unpatch(self) -> None:
        """Unpatch"""

    def patch(self) -> None:
        """Patch"""

        if not self._is_patched:
            result = self._patch()
            self._is_patched = True
            return result

        _LOG.warning("Attempting to patch while already patched")

        return None

    def unpatch(self) -> None:
        """Unpatch"""

        if self._is_patched:
            result = self._unpatch()
            self._is_patched = False
            return result

        _LOG.warning("Attempting to unpatch while already unpatched")

        return None


__all__ = ["BasePatcher"]
