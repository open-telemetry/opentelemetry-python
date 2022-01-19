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

import logging
import os
from abc import ABC, abstractmethod
from enum import Enum
from os import environ, linesep
from sys import stdout
from threading import Condition, Event, Lock, Thread
from typing import IO, Callable, Iterable, Optional, Sequence

from opentelemetry.context import (
    _SUPPRESS_INSTRUMENTATION_KEY,
    attach,
    detach,
    set_value,
)
from opentelemetry.sdk._metrics.metric_reader import MetricReader
from opentelemetry.sdk._metrics.point import Metric

_logger = logging.getLogger(__name__)


class MetricExportResult(Enum):
    SUCCESS = 0
    FAILURE = 1


class MetricExporter(ABC):
    """Interface for exporting metrics.

    Interface to be implemented by services that want to export metrics received
    in their own format.
    """

    @abstractmethod
    def export(self, metrics: Sequence[Metric]) -> "MetricExportResult":
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
        formatter: Callable[[Metric], str] = lambda metric: metric.to_json()
        + linesep,
    ):
        self.out = out
        self.formatter = formatter

    def export(self, metrics: Sequence[Metric]) -> MetricExportResult:
        for metric in metrics:
            self.out.write(self.formatter(metric))
        self.out.flush()
        return MetricExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


class PeriodicExportingMetricReader(MetricReader):
    """`PeriodicExportingMetricReader` is an implementation of `MetricReader`
    that collects metrics based on a user-configurable time interval, and passes the
    metrics to the configured exporter.
    """

    def __init__(
        self,
        exporter: MetricExporter,
        export_interval_millis: Optional[float] = None,
        export_timeout_millis: Optional[float] = None,
    ) -> None:
        self._exporter = exporter
        if export_interval_millis is None:
            try:
                export_interval_millis = float(
                    environ.get("OTEL_METRIC_EXPORT_INTERVAL", 60000)
                )
            except ValueError:
                _logger.warning(
                    "Found invalid value for export interval, using default"
                )
                export_interval_millis = 60000
        if export_timeout_millis is None:
            try:
                export_timeout_millis = float(
                    environ.get("OTEL_METRIC_EXPORT_TIMEOUT", 30000)
                )
            except ValueError:
                _logger.warning(
                    "Found invalid value for export timeout, using default"
                )
                export_timeout_millis = 30000
        self._export_interval_millis = export_interval_millis
        self._export_timeout_millis = export_timeout_millis
        self._shutdown = False
        self._daemon_thread = Thread(target=self._ticker, daemon=True)
        self._condition = Condition()
        self._lock = Lock()
        self._daemon_thread.start()
        if hasattr(os, "register_at_fork"):
            os.register_at_fork(
                after_in_child=self._at_fork_reinit
            )  # pylint: disable=protected-access

    def _at_fork_reinit(self):
        self._condition = Condition()
        self._lock = Lock()
        self._daemon_thread = Thread(target=self._ticker, daemon=True)
        self._daemon_thread.start()

    def _ticker(self) -> None:
        interval_secs = self._export_interval_millis / 1e3
        while not self._shutdown:
            with self._condition:
                # might have received shutdown request
                if not self._shutdown:
                    self._condition.wait(interval_secs)
                if self._shutdown:
                    break
            self.collect()
        # one last collection below before shutting down completely
        self.collect()

    def _receive_metrics(self, metrics: Iterable[Metric]) -> None:
        token = attach(set_value(_SUPPRESS_INSTRUMENTATION_KEY, True))
        try:
            self._exporter.export(metrics)
        except Exception as e:  # pylint: disable=broad-except,invalid-name
            _logger.exception("Exception while exporting metrics %s", str(e))
        detach(token)

    def shutdown(self) -> bool:
        with self._lock:
            if self._shutdown:
                _logger.warning("Can't shutdown multiple times")
                return False
            self._shutdown = True
        with self._condition:
            self._condition.notify_all()
        self._daemon_thread.join()
        return self._exporter.shutdown()
