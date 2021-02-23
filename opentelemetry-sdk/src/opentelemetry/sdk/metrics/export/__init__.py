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

from enum import Enum
from typing import Sequence, Tuple

from opentelemetry import metrics as metrics_api
from opentelemetry.sdk.metrics.export.aggregate import Aggregator
from opentelemetry.sdk.resources import Resource


class MetricsExportResult(Enum):
    SUCCESS = 0
    FAILURE = 1


class ExportRecord:
    def __init__(
        self,
        instrument: metrics_api.InstrumentT,
        labels: Tuple[Tuple[str, str]],
        aggregator: Aggregator,
        resource: Resource,
    ):
        self.instrument = instrument
        self.labels = labels
        self.aggregator = aggregator
        self.resource = resource


class MetricsExporter:
    """Interface for exporting metrics.

    Interface to be implemented by services that want to export recorded
    metrics in its own format.
    """

    def export(
        self, export_records: Sequence[ExportRecord]
    ) -> "MetricsExportResult":
        """Exports a batch of telemetry data.

        Args:
            export_records: A sequence of `ExportRecord` s. A `ExportRecord`
                contains the metric to be exported, the labels associated
                with that metric, as well as the aggregator used to export the
                current checkpointed value.

        Returns:
            The result of the export
        """

    def shutdown(self) -> None:
        """Shuts down the exporter.

        Called when the SDK is shut down.
        """


class ConsoleMetricsExporter(MetricsExporter):
    """Implementation of `MetricsExporter` that prints metrics to the console.

    This class can be used for diagnostic purposes. It prints the exported
    metrics to the console STDOUT.
    """

    def export(
        self, export_records: Sequence[ExportRecord]
    ) -> "MetricsExportResult":
        for export_record in export_records:
            print(
                '{}(data="{}", labels="{}", value={}, resource={})'.format(
                    type(self).__name__,
                    export_record.instrument,
                    export_record.labels,
                    export_record.aggregator.checkpoint,
                    export_record.resource.attributes,
                )
            )
        return MetricsExportResult.SUCCESS
