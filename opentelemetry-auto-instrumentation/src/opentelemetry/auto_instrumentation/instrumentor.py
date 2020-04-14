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

"""
OpenTelemetry Base Instrumentor
"""

from abc import ABC, abstractmethod
from logging import getLogger

_LOG = getLogger(__name__)


class BaseInstrumentor(ABC):
    """An ABC for instrumentors"""

    _instance = None
    _is_instrumented = False

    def __new__(cls):

        if cls._instance is None:
            cls._instance = object.__new__(cls)

        return cls._instance

    @staticmethod
    def protect_instrument(method) -> None:
        def inner(self, *args, **kwargs):
            if self._is_instrumented:  # pylint: disable=protected-access
                _LOG.warning(
                    "Attempting to call %(method.__name__)s while "
                    "already instrumented"
                )
                return None

            result = method(self, *args, **kwargs)
            self._is_instrumented = True  # pylint: disable=protected-access
            return result

        return inner

    @staticmethod
    def protect_uninstrument(method) -> None:
        def inner(self, *args, **kwargs):
            if not self._is_instrumented:  # pylint: disable=protected-access
                _LOG.warning(
                    "Attempting to call %(method.__name__)s while "
                    "already uninstrumented"
                )
                return None

            result = method(self, *args, **kwargs)
            self._is_instrumented = False  # pylint: disable=protected-access
            return result

        return inner

    @abstractmethod
    def _automatic_instrument(self) -> None:
        """Instrument"""

    @abstractmethod
    def _automatic_uninstrument(self) -> None:
        """Uninstrument"""

    def automatic_instrument(self) -> None:
        """Instrument"""

        if not self._is_instrumented:
            result = self._automatic_instrument()
            self._is_instrumented = True
            return result

        _LOG.warning(
            "Attempting to automatically instrument while already instrumented"
        )

        return None

    def automatic_uninstrument(self) -> None:
        """Uninstrument"""

        if self._is_instrumented:
            result = self._automatic_uninstrument()
            self._is_instrumented = False
            return result

        _LOG.warning(
            "Attempting to automatically uninstrument while already"
            " uninstrumented"
        )

        return None


__all__ = ["BaseInstrumentor"]
