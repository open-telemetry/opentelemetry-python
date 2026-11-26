# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry.sdk.logs._internal import (
    ConcurrentMultiLogRecordProcessor,
    Logger,
    LoggerProvider,
    LogRecordDroppedAttributesWarning,
    LogRecordLimits,
    LogRecordProcessor,
    ReadableLogRecord,
    ReadWriteLogRecord,
    SynchronousMultiLogRecordProcessor,
)

for obj in [
    ConcurrentMultiLogRecordProcessor,
    LogRecordDroppedAttributesWarning,
    LogRecordLimits,
    LogRecordProcessor,
    Logger,
    LoggerProvider,
    ReadWriteLogRecord,
    ReadableLogRecord,
    SynchronousMultiLogRecordProcessor,
]:
    obj.__module__ = __name__

__all__ = [
    "ConcurrentMultiLogRecordProcessor",
    "LogRecordDroppedAttributesWarning",
    "LogRecordLimits",
    "LogRecordProcessor",
    "Logger",
    "LoggerProvider",
    "ReadWriteLogRecord",
    "ReadableLogRecord",
    "SynchronousMultiLogRecordProcessor",
]
