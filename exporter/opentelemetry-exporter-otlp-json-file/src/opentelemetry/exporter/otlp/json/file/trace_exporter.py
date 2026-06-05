# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
from collections.abc import Sequence
from os import PathLike
from typing import IO, Any, overload

from opentelemetry.exporter.otlp.json.common.trace_encoder import encode_spans
from opentelemetry.exporter.otlp.json.file._internal import _FileExporter
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

_logger = logging.getLogger(__name__)


def _encode_spans_to_dict(
    spans: Sequence[ReadableSpan],
) -> dict[str, Any] | None:
    data = encode_spans(spans)
    return data.to_dict() if data.resource_spans else None


class FileSpanExporter(SpanExporter):
    @overload
    def __init__(
        self,
        path: str | PathLike[str],
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        stream: IO[str],
    ) -> None: ...

    @overload
    def __init__(
        self,
    ) -> None: ...

    def __init__(
        self,
        path: str | PathLike[str] | None = None,
        *,
        stream: IO[str] | None = None,
    ) -> None:
        self._exporter: _FileExporter[Sequence[ReadableSpan]] = _FileExporter(
            encode=_encode_spans_to_dict,
            kind="spans",
            logger=_logger,
            path=path,
            stream=stream,
        )

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        return (
            SpanExportResult.SUCCESS
            if self._exporter.export(spans)
            else SpanExportResult.FAILURE
        )

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        self._exporter.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
