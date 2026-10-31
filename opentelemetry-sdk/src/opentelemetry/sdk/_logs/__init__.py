# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""Public names of the OpenTelemetry logs SDK.

This module re-exports the two log record wrappers, the attribute limits, the
log record processor interface with its two multiplexing implementations, the
``logging`` module bridge and ``LoggerProvider``. The implementation of all of
them lives in ``opentelemetry.sdk._logs._internal``. Import from here instead:
the layout of the private package may change between releases, while the names
listed in ``__all__`` are the ones the SDK supports.

``LogDroppedAttributesWarning`` and ``LogLimits`` are deprecated aliases kept
for callers written against the older spelling.
"""

from opentelemetry.sdk._logs._internal import (
    ConcurrentMultiLogRecordProcessor,
    LogDroppedAttributesWarning,
    Logger,
    LoggerProvider,
    LoggingHandler,
    LogLimits,
    LogRecordDroppedAttributesWarning,
    LogRecordLimits,
    LogRecordProcessor,
    ReadableLogRecord,
    ReadWriteLogRecord,
    SynchronousMultiLogRecordProcessor,
)

__all__ = [
    "ConcurrentMultiLogRecordProcessor",
    "LogDroppedAttributesWarning",
    "LogLimits",
    "LogRecordDroppedAttributesWarning",
    "LogRecordLimits",
    "LogRecordProcessor",
    "Logger",
    "LoggerProvider",
    "LoggingHandler",
    "ReadWriteLogRecord",
    "ReadableLogRecord",
    "SynchronousMultiLogRecordProcessor",
]
