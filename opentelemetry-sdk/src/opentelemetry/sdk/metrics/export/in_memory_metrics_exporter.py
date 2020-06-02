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

import threading
from typing import Sequence

from . import MetricRecord, MetricsExporter, MetricsExportResult


class InMemoryMetricsExporter(MetricsExporter):
    """Implementation of `MetricsExporter` that stores metrics in memory.

    This class can be used for testing purposes. It stores exported metrics
    in a list in memory that can be retrieved using the
    :func:`.get_exported_metrics` method.
    """

    def __init__(self):
        self._exported_metrics = []
        self._stopped = False
        self._lock = threading.Lock()

    def clear(self):
        """Clear list of collected metrics."""
        with self._lock:
            self._exported_metrics.clear()

    def export(
        self, metric_records: Sequence[MetricRecord]
    ) -> MetricsExportResult:
        if self._stopped:
            return MetricsExportResult.FAILURE

        with self._lock:
            self._exported_metrics.extend(metric_records)
        return MetricsExportResult.SUCCESS

    def get_exported_metrics(self):
        """Get list of collected metrics."""
        with self._lock:
            return tuple(self._exported_metrics)

    def shutdown(self) -> None:
        """Shuts down the exporter.

        Called when the SDK is shut down.
        """
        self._stopped = True
