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
from threading import Event, Lock, Thread
from typing import Sequence, Tuple

from opentelemetry.metrics.instrument import Instrument
from opentelemetry.metrics.meter import Meter
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
        self.instrument = instrument
        self.labels = labels
        self.aggregator = aggregator
        self.resource = resource


class Exporter(ABC):
    """Interface for exporting metrics.

    Interface to be implemented by services that want to export recorded
    metrics in its own format.
    """

    @abstractmethod
    def export(self, records: Sequence[Record]) -> "Result":
        """Exports a batch of telemetry data.

        Args:
            records: A sequence of `Record` s. A `Record`
                contains the metric to be exported, the labels associated
                with that metric, as well as the aggregator used to export the
                current checkpointed value.

        Returns:
            The result of the export
        """

    @abstractmethod
    def shutdown(self) -> None:
        """Shuts down the exporter.

        Called when the SDK is shut down.
        """


class ConsoleExporter(Exporter):
    """Implementation of `Exporter` that prints metrics to the console.

    This class can be used for diagnostic purposes. It prints the exported
    metrics to the console STDOUT.
    """

    def export(self, records: Sequence[Record]) -> "Result":
        for record in records:
            print(
                '{}(data="{}", labels="{}", value={}, resource={})'.format(
                    type(self).__name__,
                    record.instrument,
                    record.labels,
                    record.aggregator.checkpoint,
                    record.resource.attributes,
                )
            )
        return Result.SUCCESS

    def shutdown(self):
        pass


class MemoryExporter(Exporter):
    """Implementation of `Exporter` that stores metrics in memory.
    """

    def __init__(self):
        self._exported_metrics = []
        self._shutdown = False
        self._lock = Lock()

    def clear(self):
        """Clear list of exported metrics."""
        with self._lock:
            self._exported_metrics.clear()

    def export(self, records: Sequence[Record]) -> Result:
        if self._shutdown:
            return Result.FAILURE

        with self._lock:
            self._exported_metrics.extend(records)
        return Result.SUCCESS

    @property
    def exported_metrics(self):
        """Get list of exported metrics."""
        with self._lock:
            return self._exported_metrics.copy()

    def shutdown(self) -> None:
        """Shuts down the exporter.

        Called when the SDK is shut down.
        """
        self._shutdown = True


class PushExporter(Thread):
    """A push based controller, used for collecting and exporting.

    Uses a worker thread that periodically collects metrics for exporting,
    exports them and performs some post-processing.

    Args:
        meter: The meter used to get records.
        exporter: The exporter used to export records.
        interval: The collect/export interval in seconds.
    """

    daemon = True

    def __init__(self, meter: Meter, exporter: Exporter, interval: float):
        super().__init__()
        self._meter = meter
        self._exporter = exporter
        self._interval = interval
        self._finished = Event()
        self.start()

    def run(self):
        while not self._finished.wait(self._interval):
            self._tick()

    def shutdown(self):
        self._finished.set()
        # Run one more collection pass to flush metrics batched in the meter
        self._tick()

    def _tick(self):
        with self._meter.get_records() as records:
            self._exporter.export(records)
