# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""Public names of the log record export pipeline.

This module re-exports the exporter interface, its result enum, the console and
in-memory exporters, and the simple and batching log record processors. The
implementation lives in ``opentelemetry.sdk._logs._internal.export``, except
for ``InMemoryLogRecordExporter``, which lives in
``opentelemetry.sdk._logs._internal.export.in_memory_log_exporter`` and is
re-exported from there directly, because it imports this very module and so
cannot be imported by the private export package. Import from here instead of
from either private module.

``ConsoleLogExporter``, ``LogExporter``, ``LogExportResult`` and
``InMemoryLogExporter`` are deprecated aliases kept for callers written against
the older spelling.
"""

from opentelemetry.sdk._logs._internal.export import (
    BatchLogRecordProcessor,
    ConsoleLogExporter,
    ConsoleLogRecordExporter,
    LogExporter,
    LogExportResult,
    LogRecordExporter,
    LogRecordExportResult,
    SimpleLogRecordProcessor,
)

# The point module is not in the export directory to avoid a circular import.
from opentelemetry.sdk._logs._internal.export.in_memory_log_exporter import (
    InMemoryLogExporter,
    InMemoryLogRecordExporter,
)

__all__ = [
    "BatchLogRecordProcessor",
    "ConsoleLogExporter",
    "ConsoleLogRecordExporter",
    "InMemoryLogExporter",
    "InMemoryLogRecordExporter",
    "LogExportResult",
    "LogExporter",
    "LogRecordExportResult",
    "LogRecordExporter",
    "SimpleLogRecordProcessor",
]
