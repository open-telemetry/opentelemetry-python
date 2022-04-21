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
from threading import Event, RLock, Thread
from typing import IO, Callable, Iterable, List, Optional, Sequence

from opentelemetry.context import (
    _SUPPRESS_INSTRUMENTATION_KEY,
    attach,
    detach,
    set_value,
)
from opentelemetry.sdk._metrics.metric_reader import MetricReader
from opentelemetry.sdk._metrics.point import AggregationTemporality, Metric
from opentelemetry.util._once import Once

_logger = logging.getLogger(__name__)


class MetricExportResult(Enum):
    SUCCESS = 0
    FAILURE = 1


class MetricExporter(ABC):
    """Interface for exporting metrics.

    Interface to be implemented by services that want to export metrics received
    in their own format.
    """

    @property
    def preferred_temporality(self) -> AggregationTemporality:
        return AggregationTemporality.CUMULATIVE

    @abstractmethod
    def export(self, metrics: Sequence[Metric]) -> "MetricExportResult":
        """Exports a batch of telemetry data.

        Args:
            metrics: The list of `opentelemetry.sdk._metrics.point.Metric` objects to be exported

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


class InMemoryMetricReader(MetricReader):
    """Implementation of `MetricReader` that returns its metrics from :func:`get_metrics`.

    This is useful for e.g. unit tests.
    """

    def __init__(
        self,
        preferred_temporality: AggregationTemporality = AggregationTemporality.CUMULATIVE,
    ) -> None:
        super().__init__(preferred_temporality=preferred_temporality)
        self._lock = RLock()
        self._metrics: List[Metric] = []

    def get_metrics(self) -> List[Metric]:
        """Reads and returns current metrics from the SDK"""
        with self._lock:
            self.collect()
            metrics = self._metrics
            self._metrics = []
        return metrics

    def _receive_metrics(self, metrics: Iterable[Metric]):
        with self._lock:
            self._metrics = list(metrics)

    def shutdown(self):
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
        super().__init__(preferred_temporality=exporter.preferred_temporality)
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
        self._shutdown_event = Event()
        self._shutdown_once = Once()
        self._daemon_thread = Thread(target=self._ticker, daemon=True)
        self._daemon_thread.start()
        if hasattr(os, "register_at_fork"):
            os.register_at_fork(
                after_in_child=self._at_fork_reinit
            )  # pylint: disable=protected-access

    def _at_fork_reinit(self):
        self._daemon_thread = Thread(target=self._ticker, daemon=True)
        self._daemon_thread.start()

    def _ticker(self) -> None:
        interval_secs = self._export_interval_millis / 1e3
        while not self._shutdown_event.wait(interval_secs):
            self.collect()
        # one last collection below before shutting down completely
        self.collect()

    def _receive_metrics(self, metrics: Iterable[Metric]) -> None:
        if metrics is None:
            return
        token = attach(set_value(_SUPPRESS_INSTRUMENTATION_KEY, True))
        try:
            self._exporter.export(metrics)
        except Exception as e:  # pylint: disable=broad-except,invalid-name
            _logger.exception("Exception while exporting metrics %s", str(e))
        detach(token)

    def shutdown(self):
        def _shutdown():
            self._shutdown = True

        did_set = self._shutdown_once.do_once(_shutdown)
        if not did_set:
            _logger.warning("Can't shutdown multiple times")
            return

        self._shutdown_event.set()
        self._daemon_thread.join()
        self._exporter.shutdown()
