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

import abc
from enum import Enum


class MetricExportResult(Enum):
    SUCCESS = 0
    FAILURE = 1


class MetricExporter(abc.ABC):
    """Interface for exporting metrics.

    Interface to be implemented by services that want to export metrics received
    in their own format.
    """

    @abc.abstractmethod
    def shutdown(self):
        """Shuts down the exporter.

        Called when the SDK is shut down.
        """


class ConsoleMetricExporter(MetricExporter):
    """Implementation of :class:`MetricExporter` that prints metrics to the
    console.

    This class can be used for diagnostic purposes. It prints the exported
    metrics to the console STDOUT.
    """
