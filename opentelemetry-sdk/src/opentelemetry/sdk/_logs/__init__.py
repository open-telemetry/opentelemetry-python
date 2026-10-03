# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""
Deprecated alias of :mod:`opentelemetry.sdk.logs`.

.. deprecated:: 1.46.0
    This module will be removed in a future release. Use
    :mod:`opentelemetry.sdk.logs` instead.
"""

import sys
import warnings

from opentelemetry.sdk.logs import (
    ConcurrentMultiLogRecordProcessor,
    Logger,
    LoggerProvider,
    LogRecordDroppedAttributesWarning,
    LogRecordLimits,
    LogRecordProcessor,
    ReadableLogRecord,
    ReadWriteLogRecord,
    SynchronousMultiLogRecordProcessor,
    _internal,
    export,
)
from opentelemetry.sdk.logs._internal import (
    _exceptions,
    _logger_metrics,
)
from opentelemetry.sdk.logs._internal import export as _internal_export
from opentelemetry.sdk.logs._internal.export import in_memory_log_exporter

warnings.warn(
    "The opentelemetry.sdk._logs module is deprecated since version 1.46.0 "
    "and will be removed in a future release. "
    "Use opentelemetry.sdk.logs instead.",
    DeprecationWarning,
    stacklevel=2,
)

sys.modules[f"{__name__}.export"] = export
sys.modules[f"{__name__}._internal"] = _internal
sys.modules[f"{__name__}._internal._exceptions"] = _exceptions
sys.modules[f"{__name__}._internal._logger_metrics"] = _logger_metrics
sys.modules[f"{__name__}._internal.export"] = _internal_export
sys.modules[f"{__name__}._internal.export.in_memory_log_exporter"] = in_memory_log_exporter

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
