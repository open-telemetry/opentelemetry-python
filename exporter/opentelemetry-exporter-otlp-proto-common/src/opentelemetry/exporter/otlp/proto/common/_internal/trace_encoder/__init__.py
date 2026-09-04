# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


from opentelemetry.exporter.otlp._proto.common._internal.trace_encoder import (
    _SPAN_KIND_MAP,
    _encode_status,
    encode_spans,
)

__all__ = ["_SPAN_KIND_MAP", "_encode_status", "encode_spans"]
