# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
from collections.abc import Callable, Sequence
from typing import IO

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
    def __init__(
        self,
        stream: IO[str],
        formatter: Callable[[dict], str] | None = None,
    ) -> None:
        self._stream = stream
        self._formatter = formatter or _format_line
        self._shutdown = False

    def export(
        self, batch: Sequence[ReadableLogRecord]
    ) -> LogRecordExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return LogRecordExportResult.FAILURE
        try:
            lines = [
                self._formatter(resource_logs.to_dict())
                for resource_logs in encode_logs(batch).resource_logs
            ]
            self._stream.writelines(lines)
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

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True
