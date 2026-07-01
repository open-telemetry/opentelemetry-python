# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
from collections.abc import Sequence

from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk._logs.export import (
    LogRecordExporter,
    LogRecordExportResult,
)
from opentelemetry.sdk._shared_internal import DuplicateFilter

_logger = logging.getLogger(__name__)
_logger.addFilter(DuplicateFilter())


class OTLPLogExporter(LogRecordExporter):
    def export(
        self, batch: Sequence[ReadableLogRecord]
    ) -> LogRecordExportResult:
        return LogRecordExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 10_000) -> bool:
        return True
