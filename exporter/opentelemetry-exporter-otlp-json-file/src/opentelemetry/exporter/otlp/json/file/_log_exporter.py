# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from collections.abc import Sequence
from os import PathLike
from typing import IO, Any, overload

from opentelemetry.exporter.otlp.json.common._log_encoder import encode_logs
from opentelemetry.exporter.otlp.json.file._internal import FileExporter
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk._logs.export import (
    LogRecordExporter,
    LogRecordExportResult,
)
from opentelemetry.sdk._shared_internal import DuplicateFilter

_logger = logging.getLogger(__name__)
_logger.addFilter(DuplicateFilter())


def _encode_logs_to_dict(
    batch: Sequence[ReadableLogRecord],
) -> dict[str, Any] | None:
    data = encode_logs(batch)
    return data.to_dict() if data.resource_logs else None


class FileLogExporter(LogRecordExporter):
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
        self._exporter: FileExporter[Sequence[ReadableLogRecord]] = (
            FileExporter(
                encode=_encode_logs_to_dict,
                kind="logs",
                logger=_logger,
                path=path,
                stream=stream,
            )
        )

    def export(
        self, batch: Sequence[ReadableLogRecord]
    ) -> LogRecordExportResult:
        return (
            LogRecordExportResult.SUCCESS
            if self._exporter.export(batch)
            else LogRecordExportResult.FAILURE
        )

    def shutdown(self) -> None:
        self._exporter.shutdown()
