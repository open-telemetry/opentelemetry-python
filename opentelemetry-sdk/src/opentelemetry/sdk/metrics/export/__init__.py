# Copyright 2019, OpenTelemetry Authors
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

from enum import Enum
from typing import Sequence, Tuple

from .. import Metric


class MetricsExportResult(Enum):
    SUCCESS = 0
    FAILED_RETRYABLE = 1
    FAILED_NOT_RETRYABLE = 2


class MetricsExporter:
    """Interface for exporting metrics.

    Interface to be implemented by services that want to export recorded
    metrics in its own format.
    """

    def export(
        self, metric_tuples: Sequence[Tuple[Metric, Sequence[str]]]
    ) -> "MetricsExportResult":
        """Exports a batch of telemetry data.

        Args:
            metric_tuples: A sequence of metric pairs. A metric pair consists
                of a `Metric` and a sequence of strings. The sequence of
                strings will be used to get the corresponding `MetricHandle`
                from the `Metric` to export.

        Returns:
            The result of the export
        """

    def shutdown(self) -> None:
        """Shuts down the exporter.

        Called when the SDK is shut down.
        """


class ConsoleMetricsExporter(MetricsExporter):
    """Implementation of :class:`MetricsExporter` that prints metric handles
    to the console.

    This class can be used for diagnostic purposes. It prints the exported
    metric handles to the console STDOUT.
    """

    def export(
        self, metric_tuples: Sequence[Tuple[Metric, Sequence[str]]]
    ) -> "MetricsExportResult":
        for metric, label_values in metric_tuples:
            handle = metric.get_handle(label_values)
            print(
                '{}(data="{}", label_values="{}", metric_data={})'.format(
                    type(self).__name__, metric, label_values, handle
                )
            )
        return MetricsExportResult.SUCCESS
