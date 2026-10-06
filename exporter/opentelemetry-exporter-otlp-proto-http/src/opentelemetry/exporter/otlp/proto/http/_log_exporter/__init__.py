# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""
Deprecated alias of :mod:`opentelemetry.exporter.otlp.proto.http.log_exporter`.

.. deprecated:: 1.46.0
    This module will be removed in a future release. Use
    :mod:`opentelemetry.exporter.otlp.proto.http.log_exporter` instead.
"""

import warnings

from opentelemetry.exporter.otlp.proto.http.log_exporter import (
    DEFAULT_COMPRESSION,
    DEFAULT_ENDPOINT,
    DEFAULT_LOGS_EXPORT_PATH,
    DEFAULT_TIMEOUT,
    OTLPLogExporter,
)

warnings.warn(
    "The opentelemetry.exporter.otlp.proto.http._log_exporter module is deprecated since version 1.46.0 "
    "and will be removed in a future release. "
    "Use opentelemetry.exporter.otlp.proto.http.log_exporter instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "DEFAULT_COMPRESSION",
    "DEFAULT_ENDPOINT",
    "DEFAULT_LOGS_EXPORT_PATH",
    "DEFAULT_TIMEOUT",
    "OTLPLogExporter",
]
