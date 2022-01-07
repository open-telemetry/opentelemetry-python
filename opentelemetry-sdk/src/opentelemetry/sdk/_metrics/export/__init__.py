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

from abc import ABC, abstractmethod
from enum import Enum
from os import linesep
from sys import stdout
from typing import IO, Callable, Sequence

from opentelemetry.sdk._metrics.data import MetricData
from opentelemetry.sdk._metrics.measurement import Measurement


class MetricExportResult(Enum):
    SUCCESS = 0
    FAILURE = 1


class MetricExporter(ABC):
    """Interface for exporting metrics.

    Interface to be implemented by services that want to export metrics received
    in their own format.
    """

    def export(self, metrics: Sequence[MetricData]) -> "MetricExportResult":
        """Exports a batch of telemetry data.

        Args:
            metrics: The list of `opentelemetry.sdk._metrics.data.MetricData` objects to be exported

        Returns:
            The result of the export
        """

    @abstractmethod
    def shutdown(self) -> None:
        """Shuts down the exporter.

        Called when the SDK is shut down.
        """


class ConsoleMetricExporter(MetricExporter):
    """Implementation of :class:`MetricExporter` that prints metrics to the
    console.

    This class can be used for diagnostic purposes. It prints the exported
    metrics to the console STDOUT.
    """

    def __init__(
        self,
        out: IO = stdout,
        formatter: Callable[
            [Measurement], str
        ] = lambda record: record.to_json()
        + linesep,
    ):
        self.out = out
        self.formatter = formatter

    def export(self, metrics: Sequence[MetricData]) -> MetricExportResult:
        for data in metrics:
            self.out.write(self.formatter(data.log_record))
        self.out.flush()
        return MetricExportResult.SUCCESS

    def shutdown(self) -> None:
        pass
