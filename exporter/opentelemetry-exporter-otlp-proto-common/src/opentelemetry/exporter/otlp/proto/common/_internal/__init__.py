# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


from opentelemetry.exporter.otlp._proto.common._internal import (
    _encode_attributes,
    _encode_instrumentation_scope,
    _encode_key_value,
    _encode_resource,
    _encode_span_id,
    _encode_trace_id,
    _encode_value,
    _get_resource_data,
)

__all__ = ["_encode_attributes", "_encode_instrumentation_scope", "_encode_key_value", "_encode_resource", "_encode_span_id", "_encode_trace_id", "_encode_value", "_get_resource_data"]
