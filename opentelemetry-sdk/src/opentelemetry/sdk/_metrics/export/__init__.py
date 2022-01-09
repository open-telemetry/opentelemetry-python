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
import threading
from os import environ
from typing import Optional

from opentelemetry.context import (
    _SUPPRESS_INSTRUMENTATION_KEY,
    attach,
    detach,
    set_value,
)
from opentelemetry.sdk._metrics.export.metric_exporter import MetricExporter
from opentelemetry.sdk._metrics.metric_reader import MetricReader

_logger = logging.getLogger(__name__)


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
                export_interval_millis = 60000
        if export_timeout_millis is None:
            try:
                export_timeout_millis = float(
                    environ.get("OTEL_METRIC_EXPORT_TIMEOUT", 30000)
                )
            except ValueError:
                export_timeout_millis = 30000
        self._export_interval_millis = export_interval_millis
        self._export_timeout_millis = export_timeout_millis
        self._measurement_consumer = None  # odd name
        self._shutdown = False
        self._daemon_thread = threading.Thread(
            target=self.collect, daemon=True
        )
        self._condition = threading.Condition()
        self._flush_event = None  # type: Optional[threading.Event]
        self._lock = threading.Lock()
        self._daemon_thread.start()

    def _set_measurement_consumer(self, consumer) -> None:
        self._measurement_consumer = consumer

    def collect(self) -> None:
        while not self._shutdown:
            with self._condition:
                # might have received flush/shutdown request
                if not self._flush_pending and not self._shutdown:
                    self._condition.wait(self._export_interval_millis / 1e3)
                # any pending flush request would be fulfilled later
                if self._shutdown:
                    break
            # export and set flush event if exists
            self._export()
        # one last flush below before shutting down completely
        self._export()

    @property
    def _flush_pending(self) -> bool:
        return self._flush_event is not None

    def _export(self) -> None:
        token = attach(set_value(_SUPPRESS_INSTRUMENTATION_KEY, True))
        try:
            self._exporter.export(self._measurement_consumer.collect())
        except Exception as e:
            _logger.exception("Exception while exporting metrics %s", str(e))
        detach(token)

        if self._flush_event is not None:
            self._flush_event.set()
        self._flush_event = None

    def force_flush(self, timeout_millis: float = 30000) -> bool:
        with self._lock:
            if self._shutdown:
                _logger.warning("Can't perform flush after shutdown")
                return False
        with self._condition:
            flush_event = threading.Event()
            self._flush_event = flush_event
            self._condition.notify_all()
        successful = flush_event.wait(timeout_millis / 1e3)
        if not successful:
            _logger.warning("Timed out while performing force flush")
        return successful

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
