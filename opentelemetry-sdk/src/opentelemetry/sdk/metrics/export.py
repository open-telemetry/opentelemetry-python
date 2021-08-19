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
from json import dumps
from typing import Sequence, Tuple

from opentelemetry.metrics.instrument import Instrument
from opentelemetry.sdk.metrics.aggregator import Aggregator
from opentelemetry.sdk.resources import Resource


class Result(Enum):
    SUCCESS = 0
    FAILURE = 1


class Record:
    def __init__(
        self,
        instrument: Instrument,
        labels: Tuple[Tuple[str, str]],
        aggregator: Aggregator,
        resource: Resource,
    ):

        self._instrument = instrument
        self._labels = labels
        self._aggregator = aggregator
        self._resource = resource

    @property
    def instrument(self):
        return self._instrument

    @property
    def labels(self):
        return self._labels

    @property
    def aggregator(self):
        return self._aggregator

    @property
    def resource(self):
        return self._resource

    def __str__(self):
        return dumps(
            {key[1:]: value for key, value in self.__dict__.items()}, indent=4
        )


class Exporter(ABC):
    """Interface for exporting metrics.

    Interface to be implemented by services that want to export recorded
    metrics in its own format.
    """

    @abstractmethod
    def export(self, records: Sequence[Record]) -> Result:
        """Exports a batch of telemetry data.

        Args:
            records: A sequence of `Record` s. A `Record`
                contains the metric to be exported, the labels associated
                with that metric, as well as the aggregator used to export the
                current checkpointed value.

        Returns:
            The result of the export
        """


class ConsoleExporter(Exporter):
    """Implementation of `Exporter` that prints metrics to the console.

    This class can be used for diagnostic purposes. It prints the exported
    metrics to the console STDOUT.
    """

    def export(self, records: Sequence[Record]) -> "Result":
        for record in records:
            print(record)

        return Result.SUCCESS
