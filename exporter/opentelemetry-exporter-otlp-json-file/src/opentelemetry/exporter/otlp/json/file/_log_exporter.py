# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from collections.abc import Sequence
from typing import IO, Any, overload

from opentelemetry.exporter.otlp.json.common._log_encoder import encode_logs
from opentelemetry.exporter.otlp.json.file._internal import _FileExporter
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
        path: str | os.PathLike[str],
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
        path: str | os.PathLike[str] | None = None,
        *,
        stream: IO[str] | None = None,
    ) -> None:
        self._exporter: _FileExporter[Sequence[ReadableLogRecord]] = (
            _FileExporter(
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

    # pylint: disable-next=no-self-use
    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True
