# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
from collections.abc import Callable
from typing import IO

from opentelemetry.exporter.otlp.json.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.json.file._internal import (
    _format_line,
    _get_aggregation,
    _get_temporality,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    MetricExporter,
    MetricExportResult,
    MetricsData,
)
from opentelemetry.sdk.metrics.view import Aggregation

_logger = logging.getLogger(__name__)


class FileMetricExporter(MetricExporter):
    def __init__(
        self,
        stream: IO[str],
        formatter: Callable[[dict], str] | None = None,
        preferred_temporality: dict[type, AggregationTemporality]
        | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
    ) -> None:
        MetricExporter.__init__(
            self,
            preferred_temporality=_get_temporality(preferred_temporality),
            preferred_aggregation=_get_aggregation(preferred_aggregation),
        )
        self._stream = stream
        self._formatter = formatter or _format_line
        self._shutdown = False

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return MetricExportResult.FAILURE
        try:
            lines = [
                self._formatter(resource_metrics.to_dict())
                for resource_metrics in encode_metrics(
                    metrics_data
                ).resource_metrics
            ]
            self._stream.writelines(lines)
            self._stream.flush()
        # pylint: disable-next=broad-exception-caught
        except Exception as error:
            _logger.exception(
                "Failed to write metric batch to stream: %s: %s",
                type(error).__name__,
                error,
            )
            return MetricExportResult.FAILURE
        return MetricExportResult.SUCCESS

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True
