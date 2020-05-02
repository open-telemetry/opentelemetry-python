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
    """An ABC for instrumentors

    Child classes of this ABC are implemented to instrument specific third
    party libraries or frameworks either by using the
    ``opentelemetry-auto-instrumentation`` command or by calling their methods
    directly.

    Since every third party library or framework is different and has different
    instrumentation needs, more methods can be added to the child classes as
    needed to provide practical instrumentation to the end user.
    """

    _instance = None
    _is_instrumented = False

    def __new__(cls):

        if cls._instance is None:
            cls._instance = object.__new__(cls)

        return cls._instance

    @abstractmethod
    def _instrument(self, **kwargs):
        """Instrument the library"""

    @abstractmethod
    def _uninstrument(self, **kwargs):
        """Uninstrument the library"""

    def instrument(self, **kwargs):
        """Instrument the library

        This method will be called without any optional arguments by the
        ``opentelemetry-auto-instrumentation`` command. The configuration of
        the instrumentation when done in this way should be done by previously
        setting the configuration (using environment variables or any other
        mechanism) that will be used later by the code in the ``instrument``
        implementation via the global ``Configuration`` object.

        When this method is to be called directly in the user code, ``kwargs``
        should be used to pass attributes that will override the configuration
        values read by the ``Configuration`` object.

        In this way, calling this method directly without passing any optional
        values should do the very same thing that the
        ``opentelemetry-auto-instrumentation`` command does. The idea behind
        this approach is also to keep the ``Configuration`` object immutable.

        This is necessary because this object is used by all the OpenTelemetry
        components and any change to one of its attributes could break another
        component, leading to very hard to debug bugs.
        """

        if not self._is_instrumented:
            result = self._instrument(**kwargs)
            self._is_instrumented = True
            return result

        _LOG.warning("Attempting to instrument while already instrumented")

        return None

    def uninstrument(self, **kwargs):
        """Uninstrument the library"""

        if self._is_instrumented:
            result = self._uninstrument(**kwargs)
            self._is_instrumented = False
            return result

        _LOG.warning("Attempting to uninstrument while already uninstrumented")

        return None


__all__ = ["BaseInstrumentor"]
