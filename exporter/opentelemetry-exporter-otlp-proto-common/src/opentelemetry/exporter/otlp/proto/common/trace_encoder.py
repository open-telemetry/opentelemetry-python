# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


from opentelemetry.exporter.otlp.proto.common._internal.trace_encoder import (
    encode_spans,
)

__all__ = ["encode_spans"]
