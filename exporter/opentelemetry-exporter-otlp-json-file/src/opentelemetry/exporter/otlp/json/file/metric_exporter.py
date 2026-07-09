# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from typing import IO, Any, overload

from opentelemetry.exporter.otlp.json.common._internal import (
    _get_aggregation,
    _get_temporality,
)
from opentelemetry.exporter.otlp.json.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.json.file._internal import _FileExporter
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    MetricExporter,
    MetricExportResult,
    MetricsData,
)
from opentelemetry.sdk.metrics.view import Aggregation

_logger = logging.getLogger(__name__)


def _encode_metrics_to_dict(
    metrics_data: MetricsData,
) -> dict[str, Any] | None:
    data = encode_metrics(metrics_data)
    return data.to_dict() if data.resource_metrics else None


class FileMetricExporter(MetricExporter):
    @overload
    def __init__(
        self,
        path: str | os.PathLike[str],
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
        path: str | os.PathLike[str] | None = None,
        *,
        stream: IO[str] | None = None,
        preferred_temporality: dict[type, AggregationTemporality]
        | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
    ) -> None:
        MetricExporter.__init__(
            self,
            preferred_temporality=_get_temporality(preferred_temporality),
            preferred_aggregation=_get_aggregation(preferred_aggregation),
        )
        self._exporter: _FileExporter[MetricsData] = _FileExporter(
            encode=_encode_metrics_to_dict,
            kind="metrics",
            logger=_logger,
            path=path,
            stream=stream,
        )

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        return (
            MetricExportResult.SUCCESS
            if self._exporter.export(metrics_data)
            else MetricExportResult.FAILURE
        )

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        self._exporter.shutdown()

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True
