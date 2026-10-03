# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""
Deprecated alias of :mod:`opentelemetry.exporter.otlp.proto.common.log_encoder`.

.. deprecated:: 1.46.0
    This module will be removed in a future release. Use
    :mod:`opentelemetry.exporter.otlp.proto.common.log_encoder` instead.
"""

import warnings

from opentelemetry.exporter.otlp.proto.common.log_encoder import (
    encode_logs,
)

warnings.warn(
    "The opentelemetry.exporter.otlp.proto.common._log_encoder module is deprecated since version 1.46.0 "
    "and will be removed in a future release. "
    "Use opentelemetry.exporter.otlp.proto.common.log_encoder instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "encode_logs",
]
