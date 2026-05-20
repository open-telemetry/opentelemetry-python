# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
import sys
from os import PathLike
from typing import IO, overload

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
    @overload
    def __init__(
        self,
        path: str | PathLike[str],
        *,
        preferred_temporality: dict[type, AggregationTemporality]
        | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        stream: IO[str],
        preferred_temporality: dict[type, AggregationTemporality]
        | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        preferred_temporality: dict[type, AggregationTemporality]
        | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
    ) -> None: ...

    def __init__(
        self,
        path: str | PathLike[str] | None = None,
        *,
        stream: IO[str] | None = None,
        preferred_temporality: dict[type, AggregationTemporality]
        | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
    ) -> None:
        if path is not None and stream is not None:
            raise ValueError("Cannot specify both 'path' and 'stream'")
        MetricExporter.__init__(
            self,
            preferred_temporality=_get_temporality(preferred_temporality),
            preferred_aggregation=_get_aggregation(preferred_aggregation),
        )
        if path is not None:
            self._stream: IO[str] = open(  # pylint: disable=consider-using-with
                path, "a", encoding="utf-8"
            )
            self._owns_stream = True
        elif stream is not None:
            self._stream = stream
            self._owns_stream = False
        else:
            self._stream = sys.stdout
            self._owns_stream = False
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
            json_metrics_data = encode_metrics(metrics_data)
            if json_metrics_data.resource_metrics:
                self._stream.write(_format_line(json_metrics_data.to_dict()))
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
        if self._owns_stream:
            self._stream.close()

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True
