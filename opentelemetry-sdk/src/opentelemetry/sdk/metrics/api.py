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

# pylint: disable=function-redefined,too-many-ancestors

from abc import ABC, abstractmethod
from logging import getLogger

_logger = getLogger(__name__)


class MetricReader(ABC):
    def __init__(self):
        self._shutdown = False

    @abstractmethod
    def collect(self):
        pass

    def shutdown(self):
        self._shutdown = True


class MetricExporter(ABC):
    def __init__(self):
        self._shutdown = False

    @abstractmethod
    def export(self):
        pass

    def shutdown(self):
        self._shutdown = True


class View(ABC):
    pass
