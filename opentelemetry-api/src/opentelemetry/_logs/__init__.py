# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""
Deprecated alias of :mod:`opentelemetry.logs`.

.. deprecated:: 1.46.0
    This module will be removed in a future release. Use
    :mod:`opentelemetry.logs` instead.
"""

import sys
import warnings

# pylint: disable-next=useless-import-alias
from opentelemetry._logs import severity as severity
from opentelemetry.logs import (
    Logger,
    LoggerProvider,
    LogRecord,
    NoOpLogger,
    NoOpLoggerProvider,
    SeverityNumber,
    _internal,
    get_logger,
    get_logger_provider,
    set_logger_provider,
)

warnings.warn(
    "The opentelemetry._logs module is deprecated since version 1.46.0 "
    "and will be removed in a future release. "
    "Use opentelemetry.logs instead.",
    DeprecationWarning,
    stacklevel=2,
)

sys.modules[f"{__name__}._internal"] = _internal

__all__ = [
    "LogRecord",
    "Logger",
    "LoggerProvider",
    "NoOpLogger",
    "NoOpLoggerProvider",
    "SeverityNumber",
    "get_logger",
    "get_logger_provider",
    "set_logger_provider",
]
