# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from os import PathLike
from typing import IO, overload

from opentelemetry.exporter.otlp.json.common._log_encoder import encode_logs
from opentelemetry.exporter.otlp.json.file._internal import _format_line
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk._logs.export import (
    LogRecordExporter,
    LogRecordExportResult,
)
from opentelemetry.sdk._shared_internal import DuplicateFilter

_logger = logging.getLogger(__name__)
# This prevents logs generated when a log fails to be written to generate another log which fails to be written etc. etc.
_logger.addFilter(DuplicateFilter())


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
        if path is not None and stream is not None:
            raise ValueError("Cannot specify both 'path' and 'stream'")
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
        self, batch: Sequence[ReadableLogRecord]
    ) -> LogRecordExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return LogRecordExportResult.FAILURE
        try:
            logs_data = encode_logs(batch)
            if logs_data.resource_logs:
                self._stream.write(_format_line(logs_data.to_dict()))
            self._stream.flush()
        # pylint: disable-next=broad-exception-caught
        except Exception as error:
            _logger.exception(
                "Failed to write log batch to stream: %s: %s",
                type(error).__name__,
                error,
            )
            return LogRecordExportResult.FAILURE
        return LogRecordExportResult.SUCCESS

    def shutdown(self) -> None:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        if self._owns_stream:
            self._stream.close()
